"""存量实例重编号（instance-numbering-per-branch）：旧全局编号 → 品目-分公司代码-序号。

按 分公司 × 品目 分组，组内按旧编号数值序（无序号则按创建序）从 1 连续重排为
`{品目编号}-{分公司代码}-{N}`，并同步重建 InstanceSequence 计数行。

默认预览（只打印不落库）；--confirm 执行。幂等：已全部符合新格式且序列一致则输出无需重编号。
--branch 限定单个分公司（如 --branch HZ005），其余分公司一概不碰。
调出物品保留原分公司编号（他分公司名下挂着本分公司编号段）：压缩重排会与
内部编号唯一约束撞号，此类分组整组跳过待单独处理。
单据关联/序列号/图片按实例外键自动跟随；执行后旧标签失效需重打。
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.assets.models import FixedAsset, InstanceSequence


def _tail_int(code):
    """编号尾段转 int；非数字（异常格式）按 0。"""
    tail = code.rsplit('-', 1)[-1]
    return int(tail) if tail.isdigit() else 0


def _old_sort_key(inst):
    """旧编号 {品目}-{N} 按 N 排；无 N（异常格式）按创建时间排后。"""
    tail = inst.内部编号.rsplit('-', 1)[-1]
    return (0, int(tail)) if tail.isdigit() else (1, 0)


def _code_branch_segment(code, item_code):
    """按 {品目}-{分公司代码}-{N} 拆出编号里的分公司段；旧全局/异常格式返回 None。"""
    if not code.startswith(f'{item_code}-'):
        return None
    seg, _, tail = code[len(item_code) + 1:].rpartition('-')
    return seg if seg and tail.isdigit() else None


class Command(BaseCommand):
    help = (
        '存量实例重编号为 品目-分公司代码-序号（默认预览，--confirm 执行，幂等；'
        '--branch 限定分公司代码）'
    )

    def add_arguments(self, parser):
        parser.add_argument('--confirm', action='store_true', help='执行重编号（默认仅预览）')
        parser.add_argument('--branch', help='限定分公司代码（如 HZ005），只重排该分公司')

    def handle(self, *args, **options):
        confirm = options['confirm']
        scope_branch = None
        if options['branch']:
            from apps.organizations.models import Branch
            scope_branch = Branch.objects.filter(code=options['branch']).first()
            if scope_branch is None:
                raise CommandError(f'分公司代码 {options["branch"]} 不存在')
            self.stdout.write(f'限定范围：{scope_branch.name}（{scope_branch.code}）')

        groups = {}
        qs = FixedAsset.objects.select_related('branch', 'item')
        if scope_branch is not None:
            qs = qs.filter(branch=scope_branch)
        for inst in qs:
            groups.setdefault((inst.branch, inst.item), []).append(inst)

        pending = []
        skipped = []
        kept_strayed = 0
        for (branch, item), insts in sorted(
            groups.items(), key=lambda kv: (kv[0][0].name, kv[0][1].asset_code),
        ):
            # 调出带号收留侧：挂在本地但编号属于其他分公司段的实例，编号原样不动、不参与排序
            own, strayed_here = [], []
            for inst in insts:
                seg = _code_branch_segment(inst.内部编号, item.asset_code)
                (strayed_here if seg not in (None, branch.code) else own).append(inst)
            kept_strayed += len(strayed_here)
            own.sort(key=_old_sort_key)

            group_pending = []
            for n, inst in enumerate(own, start=1):
                new_code = f'{item.asset_code}-{branch.code}-{n}'
                if inst.内部编号 != new_code:
                    group_pending.append((inst, new_code))
            seq = InstanceSequence.objects.filter(item=item, branch=branch).first()
            seq_stale = not seq or seq.last_no != len(own)

            if group_pending or seq_stale:
                # 调出带号来源侧：他分公司名下还挂着本分公司编号段的实例（调出保留旧编号），
                # 压缩重排会与内部编号唯一约束撞号——整组跳过，待调出编号策略定论
                strayed = FixedAsset.objects.filter(
                    内部编号__startswith=f'{item.asset_code}-{branch.code}-',
                ).exclude(branch_id=branch.pk).exists()
                if strayed:
                    skipped.append((branch, item))
                    continue
                pending.extend(group_pending)
                if seq_stale:
                    pending.append(('__seq__', (branch, item, len(own))))

        self.stdout.write(f'实例总数 {sum(len(v) for v in groups.values())}；'
                          f'需重编号 {sum(1 for p in pending if p[0] != "__seq__")} 台；'
                          f'需重建序列 {sum(1 for p in pending if p[0] == "__seq__")} 行；'
                          f'调出带号保留不动 {kept_strayed} 台')
        for branch, item in skipped:
            self.stdout.write(self.style.WARNING(
                f'  跳过 {branch.name}（{branch.code}）× {item.asset_code}：'
                '编号段内有调出他分公司的实例（保留旧编号），压缩会撞号，需单独处理'
            ))
        for entry in pending[:20]:
            if entry[0] == '__seq__':
                _, (branch, item, last) = entry
                self.stdout.write(f'  预览 序列 {branch.name} × {item.asset_code} → {last}')
            else:
                inst, new_code = entry
                self.stdout.write(f'  预览 {inst.内部编号} → {new_code}')
        if len(pending) > 20:
            self.stdout.write(f'  ...（其余 {len(pending) - 20} 项略）')

        if not pending:
            self.stdout.write(self.style.SUCCESS('编号已全部符合新格式且序列一致，无需重编号'))
            return
        if not confirm:
            self.stdout.write(self.style.WARNING('预览完成（未落库）。加 --confirm 执行重编号'))
            return

        with transaction.atomic():
            renamed = 0
            for entry in pending:
                if entry[0] == '__seq__':
                    _, (branch, item, last) = entry
                    InstanceSequence.objects.update_or_create(
                        item=item, branch=branch, defaults={'last_no': last},
                    )
                else:
                    inst, new_code = entry
                    from apps.assets.services.instances import renumber_instance
                    renumber_instance(inst, new_code)
                    renamed += 1
            # 序列兜底：无 pending 序列项的分组也确保存在；last_no 取该编号段全库
            # 最大尾号（含调出到他分公司名下的同段编号），保证后续发号不撞既有编号
            for (branch, item), insts in groups.items():
                if not InstanceSequence.objects.filter(item=item, branch=branch).exists():
                    max_tail = max(
                        (_tail_int(c) for c in FixedAsset.objects.filter(
                            内部编号__startswith=f'{item.asset_code}-{branch.code}-',
                        ).values_list('内部编号', flat=True)),
                        default=0,
                    )
                    InstanceSequence.objects.create(
                        item=item, branch=branch, last_no=max_tail,
                    )
        self.stdout.write(self.style.SUCCESS(f'重编号完成：{renamed} 台；序列已同步'))
