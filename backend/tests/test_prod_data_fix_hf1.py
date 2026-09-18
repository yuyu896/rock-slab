"""生产数据纠错命令测试：合肥分公司资产全清（任意单据构成，同侧归零）。"""
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


def _purchase(branch, item, qty, no, status='已入库', extra_lines=()):
    fields = {
        '调拨日期': datetime.date(2025, 8, 12), '审批状态': status,
        '单据编号': no, '调入分公司': branch.name, '创建人': '测试',
    }
    t = Transfer.build('purchase', fields, 所属分公司=branch)
    t.save()
    TransferLine.objects.create(transfer=t, item=item, 行号=1, 数量=qty)
    for i, (li, lq) in enumerate(extra_lines, start=2):
        TransferLine.objects.create(transfer=t, item=li, 行号=i, 数量=lq)
    if status in ('已通过', '已入库'):
        ledger.apply_document(t)
    return Transfer.objects.get(pk=t.pk)


def _run(*args):
    out = StringIO()
    call_command('prod_data_fix_hf1', *args, stdout=out)
    return out.getvalue()


def _check_consistent():
    out = StringIO()
    call_command('check_ledger_consistency', stdout=out)
    return out.getvalue()


@pytest.fixture
def hf1(team):
    return Branch.objects.create(name='合肥分公司', code='HF001', team=team)


@pytest.mark.django_db
class TestHf1TotalWipe:
    def test_three_source_total_wipe(self, hf1, second_branch):
        inst_item = _item('HF1-I1')
        qty_item = _item('HF1-Q1', 'quantity')
        cons_item = _item('HF1-C1', 'consumable')
        # 纯实例生效单
        _purchase(hf1, inst_item, 3, 'CG20250812-004')
        # 混行生效单（实例 + 数量 + 耗材同单）
        _purchase(hf1, inst_item, 2, 'CG20250812-005',
                  extra_lines=[(qty_item, 5), (cons_item, 8)])
        # 纯数量生效单
        _purchase(hf1, qty_item, 4, 'CG20250812-006')
        # 待审批单
        _purchase(hf1, qty_item, 6, 'CG20250812-007', status='待审批')
        # 建账调整单
        ledger.apply_adjustment(hf1, qty_item, ledger.COLUMN_STOCK, 7, '建账')
        ledger.apply_adjustment(hf1, cons_item, ledger.COLUMN_STOCK, 9, '建账')
        User.objects.create_user(
            phone='13711110101', name='合肥行政', password='x',
            role='manager', status='active', branch=hf1,
        )
        # 他分公司基准
        _purchase(second_branch, inst_item, 2, 'CG20250812-099')
        ledger.apply_adjustment(second_branch, qty_item, ledger.COLUMN_STOCK, 3, '他司')

        out = _run('--apply')
        assert '已写入：删 4 单 / 2 调整单' in out and '5 实例' in out

        assert Transfer.objects.filter(to_branch=hf1).count() == 0
        assert LedgerAdjustment.objects.filter(branch=hf1).count() == 0
        assert AssetStock.objects.filter(branch=hf1).count() == 0
        assert FixedAsset.objects.filter(branch=hf1).count() == 0
        assert Branch.objects.filter(name='合肥分公司').exists()
        assert User.objects.filter(branch=hf1, name='合肥行政').exists()
        # 他司零波及
        assert FixedAsset.objects.filter(branch=second_branch, item=inst_item).count() == 2
        assert AssetStock.objects.get(branch=second_branch, item=qty_item).在库数量 == 3
        _check_consistent()

    def test_from_side_doc_rejects(self, hf1):
        qty_item = _item('HF1-Q2', 'quantity')
        ledger.apply_adjustment(hf1, qty_item, ledger.COLUMN_STOCK, 5, '建账')
        t = Transfer.build(
            'assign',
            {'调拨日期': datetime.date(2025, 8, 13), '审批状态': '已入库',
             '单据编号': 'LY20250813-001', '调出分公司': hf1.name},
            所属分公司=hf1,
        )
        t.save()
        TransferLine.objects.create(transfer=t, item=qty_item, 行号=1, 数量=2)
        ledger.apply_document(t)

        with pytest.raises(CommandError, match='调出方'):
            _run('--apply')
        assert AssetStock.objects.filter(branch=hf1).exists()  # 零变更

    def test_dry_run_and_idempotent(self, hf1):
        _purchase(hf1, _item('HF1-I2'), 1, 'CG20250812-008')
        ledger.apply_adjustment(hf1, _item('HF1-Q3'), ledger.COLUMN_STOCK, 4, '建账')

        out = _run()
        assert 'dry-run' in out
        assert FixedAsset.objects.filter(branch=hf1).count() == 1

        _run('--apply')
        out = _run('--apply')
        assert '无需处理（幂等跳过）' in out
        _check_consistent()
