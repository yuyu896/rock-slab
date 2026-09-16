"""生产数据纠错命令测试：上海分公司 A-a00007 品目维度整清（复用 0915 案A 路径）。"""
import datetime
import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from io import StringIO

from apps.assets.models import AssetStock, FixedAsset
from apps.assets.services import ledger
from apps.categories.models import Category
from apps.organizations.models import Branch
from apps.transfers.models import Transfer, TransferLine


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


def _purchase(branch, item, qty, no, extra_lines=()):
    t = Transfer.build(
        'purchase',
        {'调拨日期': datetime.date(2025, 6, 1), '审批状态': '已入库', '单据编号': no,
         '调入分公司': branch.name, '创建人': '测试'},
        所属分公司=branch,
    )
    t.save()
    TransferLine.objects.create(transfer=t, item=item, 行号=1, 数量=qty)
    for i, (li, lq) in enumerate(extra_lines, start=2):
        TransferLine.objects.create(transfer=t, item=li, 行号=i, 数量=lq)
    ledger.apply_document(t)
    return Transfer.objects.get(pk=t.pk)


def _run(*args):
    out = StringIO()
    call_command('prod_data_fix_sh1', *args, stdout=out)
    return out.getvalue()


def _check_consistent():
    out = StringIO()
    call_command('check_ledger_consistency', stdout=out)
    return out.getvalue()


@pytest.fixture
def sh1(team):
    return Branch.objects.create(name='上海分公司', code='SH001', team=team)


@pytest.mark.django_db
class TestSh1ItemWipe:
    def test_item_wipe_zero_touch_elsewhere(self, sh1, second_branch):
        from unittest.mock import patch
        from apps.assets.management.commands.prod_data_fix_sh1 import ITEM_CODE

        phone = _item('A-a00007')
        other_inst = _item('SH1-I1')
        qty_item = _item('SH1-Q1', 'quantity')
        d1 = _purchase(sh1, phone, 20, 'CG20250601-001')
        d2 = _purchase(sh1, phone, 15, 'CG20250601-002')
        keep1 = _purchase(sh1, other_inst, 2, 'CG20250601-003')
        keep2 = _purchase(sh1, qty_item, 9, 'CG20250601-004')
        other_doc = _purchase(second_branch, phone, 30, 'CG20250601-101')

        out = _run('--apply')
        assert '已写入：删 2 单 / 35 实例' in out

        assert FixedAsset.objects.filter(branch=sh1, item=phone).count() == 0
        assert not Transfer.objects.filter(pk__in=[d1.pk, d2.pk]).exists()
        assert AssetStock.objects.get(branch=sh1, item=phone).在库数量 == 0
        # 本分公司他品目不动
        assert Transfer.objects.filter(pk__in=[keep1.pk, keep2.pk]).exists()
        assert FixedAsset.objects.filter(branch=sh1, item=other_inst).count() == 2
        assert AssetStock.objects.get(branch=sh1, item=qty_item).在库数量 == 9
        # 他分公司同品目零波及
        assert Transfer.objects.filter(pk=other_doc.pk).exists()
        assert AssetStock.objects.get(branch=second_branch, item=phone).在库数量 == 30
        assert FixedAsset.objects.filter(branch=second_branch, item=phone).count() == 30
        _check_consistent()

    def test_mixed_birth_doc_rejected(self, sh1):
        phone = _item('A-a00007')
        _purchase(sh1, phone, 2, 'CG20250601-020', extra_lines=[(_item('SH1-I2'), 1)])

        with pytest.raises(CommandError, match='混行单'):
            _run('--apply')
        assert FixedAsset.objects.filter(branch=sh1, item=phone).count() == 2

    def test_mirror_mismatch_rejected(self, sh1):
        phone = _item('A-a00007')
        _purchase(sh1, phone, 3, 'CG20250601-030')
        row = AssetStock.objects.get(branch=sh1, item=phone)
        row.在库数量 = 10
        row.save(update_fields=['在库数量'])

        with pytest.raises(CommandError, match='镜像不一致'):
            _run('--apply')
        assert FixedAsset.objects.filter(branch=sh1, item=phone).count() == 3

    def test_dry_run_and_idempotent(self, sh1):
        phone = _item('A-a00007')
        _purchase(sh1, phone, 4, 'CG20250601-040')

        out = _run()
        assert 'dry-run' in out
        assert FixedAsset.objects.filter(branch=sh1, item=phone).count() == 4

        _run('--apply')
        out = _run('--apply')
        assert '无需处理（幂等跳过）' in out
        _check_consistent()
