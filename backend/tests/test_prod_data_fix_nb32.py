"""生产数据纠错命令测试：32分宁波非实例品目建账整清（实例档案保留）。"""
import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from io import StringIO

from apps.assets.models import AssetStock, FixedAsset, LedgerAdjustment
from apps.assets.services import ledger
from apps.categories.models import Category
from apps.organizations.models import Branch
from apps.transfers.models import Transfer, TransferLine


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


def _run(*args):
    out = StringIO()
    call_command('prod_data_fix_nb32', *args, stdout=out)
    return out.getvalue()


def _check_consistent():
    out = StringIO()
    call_command('check_ledger_consistency', stdout=out)
    return out.getvalue()


@pytest.fixture
def nb32(team):
    return Branch.objects.create(name='32分宁波', code='NB032', team=team)


def _seed_mixed(nb32):
    """数量 + 耗材 + 实例品目（调整单建镜像 + 直造实例，生产同形态）。"""
    q1, c1 = _item('NB-Q1'), _item('NB-C1', 'consumable')
    i1 = _item('NB-I1', 'instance')
    ledger.apply_adjustment(nb32, q1, ledger.COLUMN_STOCK, 6, '建账')
    ledger.apply_adjustment(nb32, c1, ledger.COLUMN_STOCK, 3, '建账')
    ledger.apply_adjustment(nb32, i1, ledger.COLUMN_STOCK, 2, '实例镜像建账')
    for n in range(1, 3):
        FixedAsset.objects.create(
            item=i1, 内部编号=f'{i1.asset_code}-{nb32.code}-{n:03d}',
            当前状态='在库', branch=nb32,
        )
    return q1, c1, i1


@pytest.mark.django_db
class TestNb32NonInstanceWipe:
    def test_wipe_keeps_instance_side(self, nb32, second_branch):
        q1, c1, i1 = _seed_mixed(nb32)
        ledger.apply_adjustment(second_branch, q1, ledger.COLUMN_STOCK, 9, '他分公司')

        out = _run('--apply')
        assert '已写入：删 2 调整单 / 2 台账行' in out

        assert AssetStock.objects.filter(branch=nb32, item=q1).count() == 0
        assert AssetStock.objects.filter(branch=nb32, item=c1).count() == 0
        assert LedgerAdjustment.objects.filter(
            branch=nb32, item__management_type__in=('quantity', 'consumable'),
        ).count() == 0
        # 实例侧原样
        assert AssetStock.objects.get(branch=nb32, item=i1).在库数量 == 2
        assert FixedAsset.objects.filter(branch=nb32).count() == 2
        assert LedgerAdjustment.objects.filter(branch=nb32, item=i1).count() == 1
        # 他分公司不动
        assert AssetStock.objects.get(branch=second_branch, item=q1).在库数量 == 9
        _check_consistent()

    def test_rejects_when_transfer_docs_exist(self, nb32):
        q1 = _item('NB-Q2')
        ledger.apply_adjustment(nb32, q1, ledger.COLUMN_STOCK, 5, '建账')
        t = Transfer.build(
            'purchase',
            {'调拨日期': __import__('datetime').date(2026, 9, 15), '审批状态': '已入库',
             '单据编号': 'CG20260915-001', '调入分公司': nb32.name},
            所属分公司=nb32,
        )
        t.save()
        TransferLine.objects.create(transfer=t, item=q1, 行号=1, 数量=2)
        ledger.apply_document(t)

        with pytest.raises(CommandError, match='不适用建账整清路径'):
            _run('--apply')
        assert AssetStock.objects.filter(branch=nb32, item=q1).exists()  # 零变更

    def test_rejects_mishung_instance(self, nb32):
        q1 = _item('NB-Q3')
        ledger.apply_adjustment(nb32, q1, ledger.COLUMN_STOCK, 4, '建账')
        FixedAsset.objects.create(  # 数量品目上错挂实例
            item=q1, 内部编号='NB-Q3-ERR-1', 当前状态='在库', branch=nb32,
        )

        with pytest.raises(CommandError, match='错挂实例档案'):
            _run('--apply')
        assert AssetStock.objects.filter(branch=nb32, item=q1).exists()  # 零变更

    def test_dry_run_and_idempotent(self, nb32):
        _seed_mixed(nb32)

        out = _run()
        assert 'dry-run' in out
        assert AssetStock.objects.filter(branch=nb32).count() == 3  # 未写库

        _run('--apply')
        out = _run('--apply')
        assert '无需处理（幂等跳过）' in out
        _check_consistent()
