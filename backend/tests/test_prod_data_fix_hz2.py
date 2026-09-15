"""生产数据纠错命令测试：2分杭州资产整清（实例出生单连删 + 建账成对删合体）。"""
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


def _purchase(branch, item, qty, no):
    t = Transfer.build(
        'purchase',
        {'调拨日期': datetime.date(2026, 9, 15), '审批状态': '已入库', '单据编号': no,
         '调入分公司': branch.name, '创建人': '测试'},
        所属分公司=branch,
    )
    t.save()
    TransferLine.objects.create(transfer=t, item=item, 行号=1, 数量=qty)
    ledger.apply_document(t)
    return Transfer.objects.get(pk=t.pk)


def _run(*args):
    out = StringIO()
    call_command('prod_data_fix_hz2', *args, stdout=out)
    return out.getvalue()


def _check_consistent():
    out = StringIO()
    call_command('check_ledger_consistency', stdout=out)
    return out.getvalue()


@pytest.fixture
def hz2(team):
    return Branch.objects.create(name='2分杭州', code='HZ002', team=team)


def _seed_combined(hz2):
    """生产同形态：1 张纯实例采购单（2 行）+ 数量/耗材建账调整单。"""
    p1, p2 = _item('HZ2-I1', 'instance'), _item('HZ2-I2', 'instance')
    q1, c1 = _item('HZ2-Q1'), _item('HZ2-C1', 'consumable')
    t = Transfer.build(
        'purchase',
        {'调拨日期': datetime.date(2026, 9, 15), '审批状态': '已入库',
         '单据编号': 'CG20260915-009', '调入分公司': hz2.name, '创建人': '测试'},
        所属分公司=hz2,
    )
    t.save()
    TransferLine.objects.create(transfer=t, item=p1, 行号=1, 数量=3)
    TransferLine.objects.create(transfer=t, item=p2, 行号=2, 数量=2)
    ledger.apply_document(t)
    ledger.apply_adjustment(hz2, q1, ledger.COLUMN_STOCK, 30, '建账')
    ledger.apply_adjustment(hz2, c1, ledger.COLUMN_STOCK, 15, '建账')
    return t, p1, p2, q1, c1


@pytest.mark.django_db
class TestHz2CombinedWipe:
    def test_combined_wipe_all_zero_keeps_employee(self, hz2, second_branch, admin_user):
        t, p1, p2, q1, c1 = _seed_combined(hz2)
        User.objects.create_user(
            phone='13711110001', name='杭州行政', password='x',
            role='manager', status='active', branch=hz2,
        )
        ledger.apply_adjustment(second_branch, q1, ledger.COLUMN_STOCK, 8, '他分公司')

        out = _run('--apply')
        assert '实例侧删 1 单 / 5 实例' in out
        assert '建账侧删 2 调整单 / 2 台账行' in out

        assert FixedAsset.objects.filter(branch=hz2).count() == 0
        assert AssetStock.objects.filter(branch=hz2).count() == 0
        assert LedgerAdjustment.objects.filter(branch=hz2).count() == 0
        assert not Transfer.objects.filter(pk=t.pk).exists()
        assert Branch.objects.filter(name='2分杭州').exists()  # 节点保留
        assert User.objects.filter(branch=hz2, name='杭州行政').exists()  # 员工保留
        assert AssetStock.objects.get(branch=second_branch, item=q1).在库数量 == 8
        _check_consistent()

    def test_mirror_mismatch_rejects_whole_case(self, hz2):
        _seed_combined(hz2)
        r = AssetStock.objects.filter(
            branch=hz2, item__management_type='instance',
        ).first()
        r.在库数量 = 99  # 破坏镜像
        r.save(update_fields=['在库数量'])

        with pytest.raises(CommandError, match='镜像不一致'):
            _run('--apply')
        assert FixedAsset.objects.filter(branch=hz2).count() == 5  # 两侧零变更
        assert AssetStock.objects.filter(branch=hz2, item__management_type='quantity').exists()

    def test_mishung_instance_rejects(self, hz2):
        _seed_combined(hz2)
        q1 = Category.objects.get(asset_code='HZ2-Q1')
        FixedAsset.objects.create(
            item=q1, 内部编号='HZ2-Q1-ERR-1', 当前状态='在库', branch=hz2,
        )

        with pytest.raises(CommandError, match='错挂实例档案'):
            _run('--apply')
        assert AssetStock.objects.filter(branch=hz2).count() == 4  # 零变更

    def test_dry_run_and_idempotent(self, hz2):
        _seed_combined(hz2)

        out = _run()
        assert 'dry-run' in out
        assert FixedAsset.objects.filter(branch=hz2).count() == 5

        _run('--apply')
        out = _run('--apply')
        assert '无需处理（幂等跳过）' in out
        _check_consistent()
