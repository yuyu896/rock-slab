"""生产数据纠错三案命令测试：温州实例整清 / 潍坊合并改挂 / 台州测试单删除。"""
import datetime
import pytest
from django.core.management import call_command
from io import StringIO

from apps.assets.models import AssetStock, FixedAsset
from apps.assets.services import ledger
from apps.categories.models import Category
from apps.notifications.models import Notification
from apps.organizations.models import Branch, Department
from apps.permissions.models import ManagementScope
from apps.transfers.models import Transfer, TransferLine
from apps.users.models import User


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _item(code, management_type='instance'):
    item, _ = Category.objects.get_or_create(
        asset_code=code,
        defaults={
            'asset_category': '测试类目', 'item_category': '测试分类',
            'asset_name': f'品目 {code}', 'unit': '个',
            'management_type': management_type,
        },
    )
    return item


def _purchase(branch, item, qty, no):
    """生效采购单：建单 + 明细行 + apply_document（生实例/动台账）。"""
    t = Transfer.build(
        'purchase',
        {'调拨日期': datetime.date(2025, 4, 13), '审批状态': '已入库', '单据编号': no,
         '调入分公司': branch.name, '创建人': '测试'},
        所属分公司=branch,
    )
    t.save()
    TransferLine.objects.create(transfer=t, item=item, 行号=1, 数量=qty)
    ledger.apply_document(t)
    return Transfer.objects.get(pk=t.pk)


def _run(*args):
    out = StringIO()
    call_command('prod_data_fix_20260914', *args, stdout=out)
    return out.getvalue()


def _check_consistent():
    out = StringIO()
    call_command('check_ledger_consistency', stdout=out)  # 差异即 SystemExit
    return out.getvalue()


def _notify(transfer, recipient):
    return Notification.objects.create(
        recipient=recipient, title='测试通知', content='x',
        notification_type='approval',
        related_object_type='transfer', related_object_id=str(transfer.id),
    )


@pytest.fixture
def wenzhou(team):
    return Branch.objects.create(name='温州二分', code='WZ002', team=team)


@pytest.fixture
def weifang_pair(team):
    ke = Branch.objects.create(name='潍坊分公司', code='WF001', team=team)
    er = Branch.objects.create(name='潍坊二分', code='WF002', team=team)
    return ke, er


# ---------------------------------------------------------------------------
# 案一 温州二分
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestWenzhouWipe:
    def test_wipe_instances_and_birth_docs_keep_quantity(self, wenzhou, admin_user):
        i1, i2 = _item('WZ-I1'), _item('WZ-I2')
        qty_item = _item('WZ-Q1', 'quantity')
        d1 = _purchase(wenzhou, i1, 2, 'CG20250901-001')
        d2 = _purchase(wenzhou, i2, 1, 'CG20250901-002')
        dq = _purchase(wenzhou, qty_item, 5, 'CG20250901-003')
        _notify(d1, admin_user)
        note_id = _notify(d2, admin_user).id

        out = _run('--apply')
        assert '已写入：删 2 单' in out

        assert FixedAsset.objects.filter(branch=wenzhou).count() == 0
        assert not Transfer.objects.filter(pk__in=[d1.pk, d2.pk]).exists()
        assert Transfer.objects.filter(pk=dq.pk).exists()  # 数量型单据保留
        assert Notification.objects.filter(id=note_id).count() == 0
        r1 = AssetStock.objects.get(branch=wenzhou, item=i1)
        r2 = AssetStock.objects.get(branch=wenzhou, item=i2)
        rq = AssetStock.objects.get(branch=wenzhou, item=qty_item)
        assert (r1.在库数量, r2.在库数量, rq.在库数量) == (0, 0, 5)
        _check_consistent()

    def test_reimport_numbering_continues(self, wenzhou):
        """发号序列保留：清空后重导，编号在原序号上自增不重号。"""
        i1 = _item('WZ-I3')
        _purchase(wenzhou, i1, 3, 'CG20250901-010')
        old_numbers = set(
            FixedAsset.objects.filter(branch=wenzhou, item=i1).values_list('内部编号', flat=True)
        )
        _run('--apply')
        t = _purchase(wenzhou, i1, 2, 'CG20250901-011')
        new_numbers = set(
            FixedAsset.objects.filter(branch=wenzhou, item=i1).values_list('内部编号', flat=True)
        )
        assert len(new_numbers) == 2
        assert not (new_numbers & old_numbers)  # 无重号
        assert all(n > max(old_numbers) for n in new_numbers)  # 序号自增
        _check_consistent()

    def test_precondition_mirror_mismatch_aborts(self, wenzhou):
        """镜像不一致（台账在库 ≠ 在库实例数）时前置断言拒绝，零变更。"""
        from apps.assets.models import InstanceSequence
        i1 = _item('WZ-I4')
        _purchase(wenzhou, i1, 2, 'CG20250901-020')
        row = AssetStock.objects.get(branch=wenzhou, item=i1)
        row.在库数量 = 5  # 直改破坏镜像（tests 在架构白名单内）
        row.save(update_fields=['在库数量'])

        from django.core.management.base import CommandError
        with pytest.raises(CommandError, match='镜像不一致'):
            _run('--apply')
        assert FixedAsset.objects.filter(branch=wenzhou).count() == 2  # 未动


# ---------------------------------------------------------------------------
# 案二 潍坊合并
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestWeifangMerge:
    def _seed_pair(self, ke, er, admin_user):
        overlap = _item('WF-A', 'quantity')
        only_er = _item('WF-B', 'quantity')
        ledger.apply_adjustment(ke, overlap, ledger.COLUMN_STOCK, 5, '分公司底数')
        ledger.apply_adjustment(er, overlap, ledger.COLUMN_STOCK, 3, '二分底数')
        ledger.apply_adjustment(er, only_er, ledger.COLUMN_STOCK, 2, '二分独有')
        doc = _purchase(er, _item('WF-C', 'quantity'), 4, 'CG20250901-101')
        user = User.objects.create_user(
            phone='13700000099', name='二分行政', password='x',
            role='manager', status='active', branch=er,
        )
        ManagementScope.objects.create(user=user, branch=er)
        Department.objects.create(branch=ke, name='行政部')
        Department.objects.create(branch=er, name='行政部')
        Department.objects.create(branch=er, name='业务部')
        return overlap, only_er, doc, user

    def test_merge_reattributes_everything(self, weifang_pair, admin_user):
        ke, er = weifang_pair
        overlap, only_er, doc, user = self._seed_pair(ke, er, admin_user)

        out = _run('--apply')
        assert '节点已删' in out

        assert not Branch.objects.filter(name='潍坊二分').exists()
        # 台账：交集相加 / 独有改挂
        assert AssetStock.objects.get(branch=ke, item=overlap).在库数量 == 8
        assert AssetStock.objects.get(branch=ke, item=only_er).在库数量 == 2
        assert AssetStock.objects.filter(branch=er).count() == 0
        # 单据：外键 + 单头文本同步
        doc.refresh_from_db()
        assert doc.to_branch_id == ke.id and doc.调入分公司 == '潍坊分公司'
        # 调整单随迁（对账口径）
        from apps.assets.models import LedgerAdjustment
        assert LedgerAdjustment.objects.filter(branch=er).count() == 0
        assert LedgerAdjustment.objects.filter(branch=ke).count() == 3
        # 员工与授权迁移
        user.refresh_from_db()
        assert user.branch_id == ke.id
        assert ManagementScope.objects.filter(user=user, branch=ke).exists()
        assert ManagementScope.objects.filter(branch=er).count() == 0
        # 部门字典删除、分公司部门保留
        assert Department.objects.filter(branch=er).count() == 0
        assert Department.objects.filter(branch=ke, name='行政部').exists()
        _check_consistent()

    def test_scope_dedup_when_target_already_granted(self, weifang_pair, admin_user):
        """员工在目标已有授权时改挂去重，不产生重复行。"""
        ke, er = weifang_pair
        user = User.objects.create_user(
            phone='13700000098', name='双授权', password='x',
            role='manager', status='active', branch=er,
        )
        ManagementScope.objects.create(user=user, branch=er)
        ManagementScope.objects.create(user=user, branch=ke)

        _run('--apply')

        assert ManagementScope.objects.filter(user=user, branch=ke).count() == 1
        assert not Branch.objects.filter(name='潍坊二分').exists()


# ---------------------------------------------------------------------------
# 案三 台州测试单
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestTaizhouDocs:
    def test_delete_test_docs_full_chain(self, branch, admin_user):
        i1 = _item('TZ-I1')
        d1 = _purchase(branch, i1, 1, 'CG20250413-001')
        d2 = _purchase(branch, _item('TZ-I2'), 1, 'CG20250310-001')
        keep = _purchase(branch, _item('TZ-Q9', 'quantity'), 6, 'CG20250901-201')
        n1, n2 = _notify(d1, admin_user), _notify(d2, admin_user)
        _notify(keep, admin_user)  # 保留单的通知不动

        out = _run('--apply')
        assert '已写入 CG20250413-001' in out and '已写入 CG20250310-001' in out

        assert not Transfer.objects.filter(pk__in=[d1.pk, d2.pk]).exists()
        assert Transfer.objects.filter(pk=keep.pk).exists()
        assert FixedAsset.objects.filter(birth_line__transfer_id__in=[d1.pk, d2.pk]).count() == 0
        assert AssetStock.objects.get(branch=branch, item=i1).在库数量 == 0
        assert not Notification.objects.filter(pk__in=[n1.pk, n2.pk]).exists()
        assert Notification.objects.filter(related_object_id=str(keep.id)).exists()
        _check_consistent()

    def test_rollback_would_go_negative_aborts_untouched(self, branch):
        """库存已被后续消耗时回退为负 → 拒绝执行，数据原样。"""
        from apps.transfers.models import TransferLineInstance
        i1 = _item('TZ-I3')
        d1 = _purchase(branch, i1, 2, 'CG20250413-001')
        inst = FixedAsset.objects.filter(birth_line__transfer=d1).first()
        # 领用消耗 1 个：在库 1 / 在用 1
        assign = Transfer.build(
            'assign', {'调拨日期': datetime.date(2025, 5, 1), '审批状态': '已入库',
                       '调出分公司': branch.name, '单据编号': 'LY20250501-001'},
            所属分公司=branch,
        )
        assign.save()
        TransferLine.objects.create(transfer=assign, item=i1, 行号=1, 数量=1)
        TransferLineInstance.objects.create(
            line=assign.lines.first(), instance=inst,
        )
        ledger.apply_document(assign)

        from django.core.management.base import CommandError
        with pytest.raises(CommandError):
            _run('--apply')
        assert Transfer.objects.filter(pk=d1.pk).exists()
        assert FixedAsset.objects.filter(birth_line__transfer=d1).count() == 2


# ---------------------------------------------------------------------------
# 安全形态：dry-run / 幂等
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestSafetyShape:
    def test_dry_run_writes_nothing(self, wenzhou, weifang_pair, branch, admin_user):
        ke, er = weifang_pair
        i1 = _item('DR-I1')
        _purchase(wenzhou, i1, 2, 'CG20250901-301')
        ledger.apply_adjustment(er, _item('DR-Q1', 'quantity'), ledger.COLUMN_STOCK, 7, '底数')
        d3 = _purchase(branch, _item('DR-I2'), 1, 'CG20250413-001')

        out = _run()

        assert 'dry-run' in out
        assert FixedAsset.objects.filter(branch=wenzhou).count() == 2
        assert Branch.objects.filter(name='潍坊二分').exists()
        assert AssetStock.objects.get(branch=er, item__asset_code='DR-Q1').在库数量 == 7
        assert Transfer.objects.filter(pk=d3.pk).exists()

    def test_idempotent_rerun(self, wenzhou, weifang_pair, branch):
        ke, er = weifang_pair
        _purchase(wenzhou, _item('ID-I1'), 1, 'CG20250901-401')
        ledger.apply_adjustment(er, _item('ID-Q1', 'quantity'), ledger.COLUMN_STOCK, 4, '底数')
        _purchase(branch, _item('ID-I2'), 1, 'CG20250310-001')

        _run('--apply')
        out = _run('--apply')  # 二次执行

        assert '无实例档案，无需处理' in out
        assert '潍坊二分不存在（已合并或未建），跳过' in out
        assert '不存在（幂等跳过）' in out
        assert '对账复验' in out
        _check_consistent()
