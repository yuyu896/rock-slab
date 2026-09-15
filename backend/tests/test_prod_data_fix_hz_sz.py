"""生产数据纠错两案命令测试：杭州235建账整清 / 20分苏州实例生平连删。"""
import datetime
import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from io import StringIO

from apps.assets.models import AssetStock, FixedAsset, LedgerAdjustment
from apps.assets.services import ledger
from apps.categories.models import Category
from apps.organizations.models import Branch
from apps.permissions.models import ManagementScope
from apps.transfers.models import Transfer, TransferLine, TransferLineInstance
from apps.users.models import User


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _item(code, management_type='quantity'):
    item, _ = Category.objects.get_or_create(
        asset_code=code,
        defaults={
            'asset_category': '测试类目', 'item_category': '测试分类',
            'asset_name': f'品目 {code}', 'unit': '个',
            'management_type': management_type,
        },
    )
    return item


def _doc(action, branch, item, qty, no, *, 回收去向=None, insts=()):
    """建生效单据并过台账（实例可选链接）。"""
    fields = {
        '调拨日期': datetime.date(2026, 2, 6), '审批状态': '已通过',
        '单据编号': no, '调出分公司': branch.name, '创建人': '测试',
    }
    if action == 'purchase':
        t = Transfer.build('purchase', fields, 所属分公司=branch)
    elif action == 'recovery':
        if 回收去向:
            fields['回收去向'] = 回收去向
        t = Transfer.build('recovery', fields, 所属分公司=branch)
    else:
        t = Transfer.build(action, fields, 所属分公司=branch)
    t.save()
    line = TransferLine.objects.create(transfer=t, item=item, 行号=1, 数量=qty)
    for inst in insts:
        TransferLineInstance.objects.create(line=line, instance=inst)
    ledger.apply_document(t)
    return Transfer.objects.get(pk=t.pk)


def _run(*args):
    out = StringIO()
    call_command('prod_data_fix_hz_sz', *args, stdout=out)
    return out.getvalue()


def _check_consistent():
    out = StringIO()
    call_command('check_ledger_consistency', stdout=out)  # 差异即 SystemExit
    return out.getvalue()


@pytest.fixture
def hz235(team):
    return Branch.objects.create(name='杭州235公共物资', code='HZ235', team=team)


@pytest.fixture
def suzhou(team):
    return Branch.objects.create(name='20分苏州', code='SZ020', team=team)


# ---------------------------------------------------------------------------
# 案1 杭州235：调整单建账成对整清
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestHz235Wipe:
    def test_paired_wipe_keeps_node_and_scope(self, hz235, second_branch, admin_user):
        q1, c1 = _item('HZ-Q1'), _item('HZ-C1', 'consumable')
        ledger.apply_adjustment(hz235, q1, ledger.COLUMN_STOCK, 100, '建账')
        ledger.apply_adjustment(hz235, c1, ledger.COLUMN_STOCK, 50, '建账')
        ledger.apply_adjustment(second_branch, q1, ledger.COLUMN_STOCK, 7, '他分公司底数')
        scope = ManagementScope.objects.create(user=admin_user, branch=hz235)

        out = _run('--apply')
        assert '已写入：删 2 调整单 / 2 台账行' in out

        assert AssetStock.objects.filter(branch=hz235).count() == 0
        assert LedgerAdjustment.objects.filter(branch=hz235).count() == 0
        assert Branch.objects.filter(name='杭州235公共物资').exists()  # 节点保留
        assert ManagementScope.objects.filter(pk=scope.pk).exists()  # 授权保留
        assert AssetStock.objects.get(branch=second_branch, item=q1).在库数量 == 7
        _check_consistent()

    def test_rejects_when_transfer_docs_exist(self, hz235):
        q1 = _item('HZ-Q2')
        ledger.apply_adjustment(hz235, q1, ledger.COLUMN_STOCK, 10, '建账')
        _doc('purchase', hz235, q1, 3, 'CG20260901-001')

        with pytest.raises(CommandError, match='不适用建账整清路径'):
            _run('--apply')
        assert AssetStock.objects.filter(branch=hz235).exists()  # 零变更
        assert LedgerAdjustment.objects.filter(branch=hz235).exists()


# ---------------------------------------------------------------------------
# 案2 20分苏州：实例生平连删（含退役）
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestSuzhouJourneyWipe:
    def _build_journey(self, suzhou):
        """复刻生产形态：X 走 领用→回收重新入库 回到在库；Y 走 领用→回收直接处置 退役。"""
        item = _item('SZJ-I1', 'instance')
        p1 = _doc('purchase', suzhou, item, 1, 'CG20260206-002')
        x = FixedAsset.objects.get(birth_line__transfer=p1)
        _doc('assign', suzhou, item, 1, 'LY20260915-007', insts=[x])
        _doc('recovery', suzhou, item, 1, 'HS20260206-001', insts=[x])  # restock
        p2 = _doc('purchase', suzhou, item, 1, 'CG20240818-002')
        y = FixedAsset.objects.get(birth_line__transfer=p2)
        _doc('assign', suzhou, item, 1, 'LY20260915-008', insts=[y])
        _doc('recovery', suzhou, item, 1, 'HS20260206-002', 回收去向='dispose', insts=[y])
        return item, x, y

    def test_journey_wipe_aggregate_rollback(self, suzhou):
        item, x, y = self._build_journey(suzhou)
        assert FixedAsset.objects.filter(branch=suzhou).count() == 2
        assert AssetStock.objects.get(branch=suzhou, item=item).在库数量 == 1  # 生产同款现值

        out = _run('--apply')
        assert '已写入：删 6 单 / 2 实例' in out

        assert FixedAsset.objects.filter(branch=suzhou).count() == 0
        assert Transfer.objects.filter(
            单据编号__in=['CG20260206-002', 'CG20240818-002', 'LY20260915-007',
                        'LY20260915-008', 'HS20260206-001', 'HS20260206-002'],
        ).count() == 0
        assert AssetStock.objects.get(branch=suzhou, item=item).在库数量 == 0
        _check_consistent()

    def test_scope_violation_rejects(self, suzhou, second_branch):
        item = _item('SZJ-I2', 'instance')
        p1 = _doc('purchase', suzhou, item, 1, 'CG20260206-003')
        x = FixedAsset.objects.get(birth_line__transfer=p1)
        a1 = _doc('assign', suzhou, item, 1, 'LY20260915-009', insts=[x])
        # 他分公司实例被本分公司单据行误链 → 越界
        other_item = _item('SZJ-I3', 'instance')
        p_other = _doc('purchase', second_branch, other_item, 1, 'CG20260206-004')
        other_inst = FixedAsset.objects.get(birth_line__transfer=p_other)
        TransferLineInstance.objects.create(line=a1.lines.first(), instance=other_inst)

        with pytest.raises(CommandError, match='越界'):
            _run('--apply')
        assert FixedAsset.objects.filter(branch=suzhou).count() == 1  # 零变更
        assert AssetStock.objects.get(branch=suzhou, item=item).在用数量 == 1


# ---------------------------------------------------------------------------
# 安全形态
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestSafetyShape:
    def test_dry_run_writes_nothing(self, hz235, suzhou):
        q1 = _item('DRH-Q1')
        ledger.apply_adjustment(hz235, q1, ledger.COLUMN_STOCK, 30, '建账')
        item = _item('DRH-I1', 'instance')
        _doc('purchase', suzhou, item, 1, 'CG20260206-005')

        out = _run()

        assert 'dry-run' in out
        assert AssetStock.objects.filter(branch=hz235).exists()
        assert FixedAsset.objects.filter(branch=suzhou).exists()

    def test_idempotent_rerun(self, hz235, suzhou):
        ledger.apply_adjustment(hz235, _item('IDH-Q1'), ledger.COLUMN_STOCK, 5, '建账')
        item = _item('IDH-I1', 'instance')
        _doc('purchase', suzhou, item, 1, 'CG20260206-006')

        _run('--apply')
        out = _run('--apply')

        assert '无调整单且无台账行，无需处理' in out
        assert '无实例档案，无需处理' in out
        assert '对账复验' in out
        _check_consistent()
