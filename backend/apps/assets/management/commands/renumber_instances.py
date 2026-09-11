"""存量实例重编号（instance-numbering-per-branch）：旧全局编号 → 品目-分公司代码-序号。

按 分公司 × 品目 分组，组内按旧编号数值序（无序号则按创建序）从 1 连续重排为
`{品目编号}-{分公司代码}-{N}`，并同步重建 InstanceSequence 计数行。

默认预览（只打印不落库）；--confirm 执行。幂等：已全部符合新格式且序列一致则输出无需重编号。
单据关联/序列号/图片按实例外键自动跟随；执行后旧标签失效需重打。
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.assets.models import FixedAsset, InstanceSequence


def _old_sort_key(inst):
    """旧编号 {品目}-{N} 按 N 排；无 N（异常格式）按创建时间排后。"""
    tail = inst.内部编号.rsplit('-', 1)[-1]
    return (0, int(tail)) if tail.isdigit() else (1, 0)


class Command(BaseCommand):
    help = '存量实例重编号为 品目-分公司代码-序号（默认预览，--confirm 执行，幂等）'

    def handle(self, *args, **options):
        confirm = options['confirm']
        groups = {}
        for inst in FixedAsset.objects.select_related('branch', 'item'):
            groups.setdefault((inst.branch, inst.item), []).append(inst)

        pending = []
        for (branch, item), insts in sorted(
            groups.items(), key=lambda kv: (kv[0][0].name, kv[0][1].asset_code),
        ):
            insts.sort(key=_old_sort_key)
            for n, inst in enumerate(insts, start=1):
                new_code = f'{item.asset_code}-{branch.code}-{n}'
                if inst.内部编号 != new_code:
                    pending.append((inst, new_code))
            seq = InstanceSequence.objects.filter(item=item, branch=branch).first()
            if not seq or seq.last_no != len(insts):
                pending.append(('__seq__', (branch, item, len(insts))))

        self.stdout.write(f'实例总数 {sum(len(v) for v in groups.values())}；'
                          f'需重编号 {sum(1 for p in pending if p[0] != "__seq__")} 台；'
                          f'需重建序列 {sum(1 for p in pending if p[0] == "__seq__")} 行')
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
            # 序列兜底：无 pending 序列项的分组也确保存在（重编号后新增从 N+1 起）
            for (branch, item), insts in groups.items():
                if not InstanceSequence.objects.filter(item=item, branch=branch).exists():
                    InstanceSequence.objects.create(
                        item=item, branch=branch, last_no=len(insts),
                    )
        self.stdout.write(self.style.SUCCESS(f'重编号完成：{renamed} 台；序列已同步'))

    def add_arguments(self, parser):
        parser.add_argument('--confirm', action='store_true', help='执行重编号（默认仅预览）')
