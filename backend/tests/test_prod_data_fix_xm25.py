"""生产数据纠错命令测试：25分厦门资产整清（建账成对删 + 未生效单据清理）。"""
import datetime
import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from io import StringIO

from apps.assets.models import AssetStock, FixedAsset, LedgerAdjustment
from apps.assets.services import ledger
from apps.categories.models import Category
from apps.organizations.models import Branch
from apps.transfers.models import Transfer, TransferLine
from apps.users.models import User


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


def _purchase(branch, item, qty, no, status='待审批'):
    t = Transfer.build(
        'purchase',
        {'调拨日期': datetime.date(2025, 7, 25), '审批状态': status, '单据编号': no,
         '调入分公司': branch.name, '创建人': '测试'},
        所属分公司=branch,
    )
    t.save()
    TransferLine.objects.create(transfer=t, item=item, 行号=1, 数量=qty)
    if status in ('已通过', '已入库'):
        ledger.apply_document(t)
    return t


def _run(*args):
    out = StringIO()
    call_command('prod_data_fix_xm25', *args, stdout=out)
    return out.getvalue()


def _check_consistent():
    out = StringIO()
    call_command('check_ledger_consistency', stdout=out)
    return out.getvalue()


@pytest.fixture
def xm25(team):
    return Branch.objects.create(name='25分厦门', code='XM025', team=team)


@pytest.mark.django_db
class TestXm25Wipe:
    def test_paired_plus_pending_wipe(self, xm25, second_branch, admin_user):
        q1, c1 = _item('XM-Q1'), _item('XM-C1', 'consumable')
        i1 = _item('XM-I1', 'instance')
        ledger.apply_adjustment(xm25, q1, ledger.COLUMN_STOCK, 20, '建账')
        ledger.apply_adjustment(xm25, c1, ledger.COLUMN_STOCK, 35, '建账')
        d1 = _purchase(xm25, i1, 1, 'CG20250725-005')
        d2 = _purchase(xm25, i1, 2, 'CG20250726-015')
        User.objects.create_user(
            phone='13711110002', name='厦门行政', password='x',
            role='manager', status='active', branch=xm25,
        )
        # 他分公司的生效采购不受影响
        keep = _purchase(second_branch, i1, 3, 'CG20250726-099', status='已入库')

        out = _run('--apply')
        assert '已写入：删 2 调整单 / 2 台账行 / 2 未生效单据' in out

        assert AssetStock.objects.filter(branch=xm25).count() == 0
        assert LedgerAdjustment.objects.filter(branch=xm25).count() == 0
        assert not Transfer.objects.filter(pk__in=[d1.pk, d2.pk]).exists()
        assert Branch.objects.filter(name='25分厦门').exists()
        assert User.objects.filter(branch=xm25, name='厦门行政').exists()
        # 待审批单删除零回退：无 apply_document，无需验证台账；他分公司生效单保留
        assert Transfer.objects.filter(pk=keep.pk).exists()
        assert AssetStock.objects.get(branch=second_branch, item=i1).在库数量 == 3
        _check_consistent()

    def test_rejects_when_effective_doc_exists(self, xm25):
        q1 = _item('XM-Q2')
        ledger.apply_adjustment(xm25, q1, ledger.COLUMN_STOCK, 10, '建账')
        _purchase(xm25, _item('XM-I2', 'instance'), 1, 'CG20250726-020', status='已入库')

        with pytest.raises(CommandError, match='存在生效单据'):
            _run('--apply')
        assert AssetStock.objects.filter(branch=xm25, item=q1).exists()  # 零变更

    def test_rejects_when_instances_exist(self, xm25):
        q1 = _item('XM-Q3')
        ledger.apply_adjustment(xm25, q1, ledger.COLUMN_STOCK, 5, '建账')
        _purchase(xm25, _item('XM-I3', 'instance'), 1, 'CG20250726-021', status='已入库')
        # 生效采购已生实例 → 双断言中实例断言兜底
        with pytest.raises(CommandError):
            _run('--apply')

    def test_dry_run_and_idempotent(self, xm25):
        ledger.apply_adjustment(xm25, _item('XM-Q4'), ledger.COLUMN_STOCK, 7, '建账')
        _purchase(xm25, _item('XM-I4', 'instance'), 1, 'CG20250726-022')

        out = _run()
        assert 'dry-run' in out
        assert AssetStock.objects.filter(branch=xm25).exists()

        _run('--apply')
        out = _run('--apply')
        assert '无需处理（幂等跳过）' in out
        _check_consistent()
