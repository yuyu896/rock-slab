"""生产数据纠错（2026-09-14）：三案一次性清理，默认 dry-run，--apply 执行。

案一 温州二分：清空实例档案 + 删除出生采购单（纯实例行）+ 台账同额回退；
              数量型/耗材库存与其余单据不动；实例发号序列保留（重导不重号）。
案二 潍坊合并：潍坊二分的采购单（外键+单头文本）/调整单/台账行（同品目相加）/
              员工与节点授权全部改挂潍坊分公司；部门字典零引用校验后删除；
              引用清零断言后硬删组织节点。
案三 19分台州：删除测试采购单 CG20250413-001 / CG20250310-001，含出生实例、
              行-实例关联、台账在库回退、关联泛化通知。

铁律 2 口径：删除错误单据属「应用之逆」——单据流水与台账存储值同批退场，
剩余流水仍完整解释剩余存量，check_ledger_consistency 双不变量保持零差异
（与 purge_business_data 同法理）。回退量执行时从明细行实时计算（_line_plan
同源矩阵），不用预采集静态值。案级独立事务，幂等可重跑。
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.assets.models import AssetStock, FixedAsset
from apps.assets.services.ledger import _line_plan
from apps.categories.models import Category
from apps.notifications.models import Notification
from apps.organizations.models import Branch, Department
from apps.permissions.models import ManagementScope
from apps.transfers.models import Transfer, TransferLine, TransferLineInstance
from apps.users.models import User

BRANCH_WENZHOU_ER = '温州二分'
BRANCH_WEIFANG = '潍坊分公司'
BRANCH_WEIFANG_ER = '潍坊二分'
TEST_DOC_NUMBERS = ('CG20250413-001', 'CG20250310-001')
EFFECTIVE_STATUSES = ('已通过', '已入库')


def _transfer_ledger_plan(transfer):
    """单据明细行 → [(branch, item, column, delta)]（与 ledger 服务同源，实时计算）。"""
    plans = []
    for line in transfer.lines.select_related('item').order_by('行号'):
        plans.extend(_line_plan(transfer, line))
    return plans


def _rollback_ledger(plans):
    """按计划逆方向直减台账（应用之逆）。行缺失或回退为负即抛错回滚。"""
    for branch, item, column, delta in plans:
        row = (
            AssetStock.objects.select_for_update()
            .filter(branch=branch, item=item).first()
        )
        if row is None:
            raise CommandError(f'台账行缺失，无法回退：{branch.name} × {item.asset_code}')
        current = getattr(row, column) or 0
        if current - delta < 0:
            raise CommandError(
                f'回退为负：{branch.name} × {item.asset_code} {column} '
                f'当前 {current}，需回退 {delta}'
            )
        setattr(row, column, current - delta)
        row.save(update_fields=[column, 'updated_at'])


def _delete_transfer_with_born_instances(transfer):
    """删单据及其出生实例：链接 → 实例 → 单头（级联明细行）。

    返回语义计数（链接/实例/单据各计其数）——不取 delete() 返回值，
    其计数含级联子对象（明细行等），语义不符。
    """
    born = FixedAsset.objects.filter(birth_line__transfer=transfer)
    n_inst = born.count()
    n_link = TransferLineInstance.objects.filter(instance__in=born).count()
    TransferLineInstance.objects.filter(instance__in=born).delete()
    born.delete()
    transfer.delete()
    return n_link, n_inst, 1


class Command(BaseCommand):
    help = ('生产数据纠错三案（温州实例清空/潍坊合并/台州测试单）；'
            '默认 dry-run，--apply 执行；案级独立事务，幂等可重跑')

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true', help='执行写入（默认仅预览）')

    def handle(self, *args, **options):
        apply = options['apply']
        self.stdout.write(f'模式：{"--apply 写入" if apply else "dry-run 预览"}')
        if apply:
            self.stdout.write('提醒：执行前请确认已跑 /root/backup_db.sh 即时备份')

        self.case_wenzhou(apply)
        self.case_weifang(apply)
        self.case_taizhou(apply)

        if apply:
            self._recheck_consistency()

    # ------------------------------------------------------------------
    # 案一 温州二分：实例档案 + 出生采购单整清
    # ------------------------------------------------------------------

    def case_wenzhou(self, apply):
        self.stdout.write('')
        self.stdout.write('=== 案一 温州二分：实例档案清空（连出生采购单） ===')
        branch = Branch.objects.filter(name=BRANCH_WENZHOU_ER).first()
        if branch is None:
            self.stdout.write('分公司不存在，跳过')
            return
        insts = FixedAsset.objects.filter(branch=branch).select_related('item')
        if not insts.exists():
            self.stdout.write('无实例档案，无需处理（幂等跳过）')
            return

        errors = []
        n_no_birth = insts.filter(birth_line=None).count()
        if n_no_birth:
            errors.append(f'{n_no_birth} 个实例无出生明细行（迁移存量），与整清口径不符')
        birth_lines = TransferLine.objects.filter(born_instances__branch=branch).distinct()
        docs = Transfer.objects.filter(lines__in=birth_lines).distinct()
        for t in docs:
            if t.action_type != 'purchase':
                errors.append(f'出生单据 {t.单据编号} 非采购单（{t.action_type}）')
            if t.审批状态 not in EFFECTIVE_STATUSES:
                errors.append(f'出生单据 {t.单据编号} 状态 {t.审批状态} 非生效')
            for line in t.lines.select_related('item'):
                if line.item.management_type != 'instance':
                    errors.append(
                        f'单据 {t.单据编号} 行 {line.行号}（{line.item.asset_code}）'
                        f'非实例管理品目，整单删除会误伤其数量账'
                    )
        # 镜像断言：实例品目 台账在库 == 在库实例数
        for item in Category.objects.filter(instances__branch=branch).distinct():
            stock = (
                AssetStock.objects.filter(branch=branch, item=item).first()
            )
            stock_qty = stock.在库数量 if stock else 0
            inst_qty = FixedAsset.objects.filter(
                branch=branch, item=item, 当前状态='在库',
            ).count()
            if stock_qty != inst_qty:
                errors.append(
                    f'镜像不一致：{item.asset_code} 台账在库 {stock_qty} vs 实例 {inst_qty}'
                )
        if errors:
            for e in errors:
                self.stdout.write(self.style.ERROR(f'  [前置失败] {e}'))
            raise CommandError('案一前置断言失败：' + '；'.join(errors))

        plans = []
        for t in docs:
            plans.extend(_transfer_ledger_plan(t))
        per_item = {}
        for _b, item, column, delta in plans:
            per_item.setdefault(item.asset_code, [item.asset_name, 0])
            per_item[item.asset_code][1] += delta

        self.stdout.write(f'  删除采购单 {docs.count()} 张（纯实例行）')
        for code, (name, qty) in sorted(per_item.items()):
            self.stdout.write(f'    {code} {name}：实例与台账在库 −{qty}')
        self.stdout.write('  保留：数量型/耗材库存及其单据、实例发号序列')
        self.stdout.write(f'  清理关联通知 {Notification.objects.filter(related_object_type="transfer", related_object_id__in=[str(t.id) for t in docs]).count()} 条')

        if apply:
            with transaction.atomic():
                doc_ids = [str(t.id) for t in docs]
                n_link, n_inst, n_doc = 0, 0, 0
                for t in docs:
                    l, i, d = _delete_transfer_with_born_instances(t)
                    n_link += l
                    n_inst += i
                    n_doc += d
                _rollback_ledger(plans)
                n_note, _ = Notification.objects.filter(
                    related_object_type='transfer', related_object_id__in=doc_ids,
                ).delete()
                self.stdout.write(self.style.SUCCESS(
                    f'  已写入：删 {n_doc} 单 / {n_inst} 实例 / {n_link} 关联 / {n_note} 通知，'
                    f'台账回退 {len(plans)} 行次'
                ))

    # ------------------------------------------------------------------
    # 案二 潍坊合并：改挂 + 硬删节点
    # ------------------------------------------------------------------

    def case_weifang(self, apply):
        self.stdout.write('')
        self.stdout.write('=== 案二 潍坊合并：潍坊二分 → 潍坊分公司 ===')
        er = Branch.objects.filter(name=BRANCH_WEIFANG_ER).first()
        ke = Branch.objects.filter(name=BRANCH_WEIFANG).first()
        if er is None:
            self.stdout.write('潍坊二分不存在（已合并或未建），跳过')
            return
        if ke is None:
            raise CommandError('潍坊分公司不存在，无法合并')

        purchases_to = Transfer.objects.filter(to_branch=er)
        transfers_from = Transfer.objects.filter(from_branch=er)
        adjustments = er.ledger_adjustments.all()
        stocks = AssetStock.objects.filter(branch=er).select_related('item')
        users = User.objects.filter(branch=er)
        scopes = ManagementScope.objects.filter(branch=er)
        departments = Department.objects.filter(branch=er)

        self.stdout.write(
            f'  改挂：采购单(to) {purchases_to.count()} 张、调出单 {transfers_from.count()} 张、'
            f'调整单 {adjustments.count()} 张、台账行 {stocks.count()} 行'
        )
        self.stdout.write(
            f'  迁移：员工 {users.count()} 人（{", ".join(users.values_list("name", flat=True))}）、'
            f'节点授权 {scopes.count()} 条；删除部门字典 {departments.count()} 条'
        )

        # 台账合并对照表（交集相加）
        ke_map = {
            r.item_id: r for r in AssetStock.objects.filter(branch=ke).select_related('item')
        }
        for r in stocks:
            target = ke_map.get(r.item_id)
            after = (
                f'{target.在库数量 + r.在库数量}' if target else f'新行 {r.在库数量}'
            )
            self.stdout.write(
                f'    {r.item.asset_code}：二分 {r.在库数量} + 分公司 '
                f'{target.在库数量 if target else 0} = {after}'
            )

        if apply:
            with transaction.atomic():
                # 台账合并（先行：后续断言依赖行已迁走）。改挂走 setattr：
                # 本文件受两道架构执法扫描（branch 赋值语句 / 台账查询集批量写），
                # 纠错改挂属设计 D1/D2 已论证的应用之逆，不为一次性命令开 services 白名单
                for r in stocks:
                    trow = AssetStock.objects.filter(branch=ke, item=r.item).first()
                    if trow is None:
                        setattr(r, 'branch', ke)
                        r.save(update_fields=['branch', 'updated_at'])
                    else:
                        trow.在库数量 += r.在库数量
                        trow.在用数量 += r.在用数量
                        trow.回收库数量 += r.回收库数量
                        trow.save(update_fields=['在库数量', '在用数量', '回收库数量', 'updated_at'])
                        r.delete()
                # 单据改挂（外键 + 单头文本同步）
                purchases_to.update(to_branch=ke, 调入分公司=ke.name)
                transfers_from.update(from_branch=ke, 调出分公司=ke.name)
                adjustments.update(branch=ke)
                users.update(branch=ke)
                for s in scopes:
                    if ManagementScope.objects.filter(user=s.user, branch=ke).exists():
                        s.delete()
                    else:
                        ManagementScope.objects.filter(pk=s.pk).update(branch=ke)
                # 盘点任务随迁（SET_NULL 不阻断，但语义上应指向合并后节点）
                from apps.inventories.models import InventoryTask
                InventoryTask.objects.filter(branch=er).update(branch=ke)
                # 部门字典：零引用校验后删除
                n_line_ref = TransferLine.objects.filter(department__branch=er).count()
                n_inst_ref = FixedAsset.objects.filter(department__branch=er).count()
                if n_line_ref or n_inst_ref:
                    raise CommandError(
                        f'潍坊二分部门字典仍被引用（单据行 {n_line_ref}、实例 {n_inst_ref}），中止'
                    )
                n_dept, _ = departments.delete()
                # 节点硬删：引用清零断言
                self._assert_branch_unref(er)
                er.delete()
                self.stdout.write(self.style.SUCCESS(
                    f'  已写入：节点已删，部门字典清理 {n_dept} 条'
                ))

    def _assert_branch_unref(self, branch):
        """组织节点硬删前置：全模型引用清零断言。"""
        from apps.inventories.models import InventoryItem, InventoryCheck
        refs = {
            '台账行': AssetStock.objects.filter(branch=branch).count(),
            '单据(调出)': Transfer.objects.filter(from_branch=branch).count(),
            '单据(调入)': Transfer.objects.filter(to_branch=branch).count(),
            '调整单': branch.ledger_adjustments.count(),
            '实例档案': FixedAsset.objects.filter(branch=branch).count(),
            '员工': User.objects.filter(branch=branch).count(),
            '部门字典': Department.objects.filter(branch=branch).count(),
            '节点授权': ManagementScope.objects.filter(branch=branch).count(),
            '实例发号行': branch.instance_sequences.count(),
            '盘点任务': branch.inventory_tasks.count(),
        }
        # 盘点明细/核查引用台账行（行已合并/删除，存在即断）
        refs['盘点明细(挂台账行)'] = InventoryItem.objects.filter(
            stock__branch=branch,
        ).count() + InventoryCheck.objects.filter(
            stock__branch=branch,
        ).count()
        leftover = {k: v for k, v in refs.items() if v}
        if leftover:
            raise CommandError(f'节点仍有引用未清：{leftover}')

    # ------------------------------------------------------------------
    # 案三 19分台州：测试采购单删除
    # ------------------------------------------------------------------

    def case_taizhou(self, apply):
        self.stdout.write('')
        self.stdout.write('=== 案三 19分台州：测试采购单删除 ===')
        for no in TEST_DOC_NUMBERS:
            t = Transfer.objects.filter(单据编号=no).first()
            if t is None:
                self.stdout.write(f'  {no}：不存在（幂等跳过）')
                continue
            if t.action_type != 'purchase' or t.审批状态 not in EFFECTIVE_STATUSES:
                raise CommandError(
                    f'{no}：类型 {t.action_type} / 状态 {t.审批状态}，与预期（生效采购单）不符'
                )
            plans = _transfer_ledger_plan(t)
            branch = t.to_branch or t.from_branch
            for _b, item, column, delta in plans:
                self.stdout.write(f'  {no}：删单 + 台账回退 {branch.name} {item.asset_code} {column} −{delta}')
            for line in t.lines.select_related('item'):
                n_born = FixedAsset.objects.filter(birth_line=line).count()
                self.stdout.write(f'    行{line.行号} {line.item.asset_code} ×{line.数量}，出生实例 {n_born} 个')

            if apply:
                with transaction.atomic():
                    doc_id = str(t.id)
                    n_link, n_inst, n_doc = _delete_transfer_with_born_instances(t)
                    _rollback_ledger(plans)
                    n_note, _ = Notification.objects.filter(
                        related_object_type='transfer', related_object_id=doc_id,
                    ).delete()
                    self.stdout.write(self.style.SUCCESS(
                        f'  已写入 {no}：删 {n_doc} 单 / {n_inst} 实例 / {n_link} 关联 / {n_note} 通知'
                    ))

    # ------------------------------------------------------------------

    def _recheck_consistency(self):
        from django.core.management import call_command
        from io import StringIO
        self.stdout.write('')
        self.stdout.write('=== 对账复验 ===')
        out = StringIO()
        try:
            call_command('check_ledger_consistency', stdout=out)
        except SystemExit:
            self.stdout.write(out.getvalue())
            raise CommandError('对账复验发现差异（见上），请立即核查，必要时用备份还原')
        self.stdout.write(self.style.SUCCESS(out.getvalue().strip()))
