"""生产数据纠错命令测试：北京三分手动点删（归零删行、空行删单）。"""
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


def _item(code):
    item, _ = Category.objects.get_or_create(
        asset_code=code,
        defaults={
            'asset_category': '测试类目', 'item_category': '测试分类',
            'asset_name': f'品目 {code}', 'unit': '个',
            'management_type': 'instance',
        },
    )
    return item


def _run(*args):
    out = StringIO()
    call_command('prod_data_fix_bj3_point', *args, stdout=out)
    return out.getvalue()


def _check_consistent():
    out = StringIO()
    call_command('check_ledger_consistency', stdout=out)
    return out.getvalue()


@pytest.fixture
def bj3(team):
    return Branch.objects.create(name='北京三分', code='BJ003', team=team)


def _doc(branch, item, lines, no):
    """建生效采购单：lines = [(qty,)] 或 [(qty, extra_item), ...]"""
    t = Transfer.build(
        'purchase',
        {'调拨日期': datetime.date(2026, 8, 6), '审批状态': '已入库', '单据编号': no,
         '调入分公司': branch.name, '创建人': '测试'},
        所属分公司=branch,
    )
    t.save()
    for i, ln in enumerate(lines, start=1):
        TransferLine.objects.create(transfer=t, item=ln[1], 行号=i, 数量=ln[0])
    ledger.apply_document(t)
    return Transfer.objects.get(pk=t.pk)


@pytest.mark.django_db
class TestBj3PointDelete:
    def test_single_line_doc_deleted_entirely(self, bj3, second_branch):
        from unittest.mock import patch
        from apps.assets.management.commands.prod_data_fix_bj3_point import TARGET_NUMBER

        item = _item('BJ3P-I1')
        d = _doc(bj3, item, [(1, item)], 'CG20260806-023')
        _doc(second_branch, item, [(2, item)], 'CG20260806-099')  # 他司基准
        target = FixedAsset.objects.get(birth_line__transfer=d)
        real_no = target.内部编号

        with patch('apps.assets.management.commands.prod_data_fix_bj3_point.TARGET_NUMBER', real_no):
            out = _run('--apply')
        assert '整单删除' in out

        assert not FixedAsset.objects.filter(pk=target.pk).exists()
        assert not Transfer.objects.filter(pk=d.pk).exists()  # 空行单据连单删
        assert AssetStock.objects.get(branch=bj3, item=item).在库数量 == 0
        assert AssetStock.objects.get(branch=second_branch, item=item).在库数量 == 2
        _check_consistent()

    def test_multi_line_doc_only_target_line_deleted(self, bj3):
        from unittest.mock import patch
        from apps.assets.management.commands.prod_data_fix_bj3_point import TARGET_NUMBER

        item, other = _item('BJ3P-I2'), _item('BJ3P-I3')
        d = _doc(bj3, item, [(1, item), (3, other)], 'CG20260806-024')
        target = FixedAsset.objects.filter(birth_line__transfer=d, item=item).first()

        with patch('apps.assets.management.commands.prod_data_fix_bj3_point.TARGET_NUMBER', target.内部编号):
            _run('--apply')

        assert Transfer.objects.filter(pk=d.pk).exists()  # 单据保留
        assert d.lines.filter(item=item).count() == 0     # 目标行删
        assert d.lines.filter(item=other).count() == 1    # 其余行原样
        assert AssetStock.objects.get(branch=bj3, item=item).在库数量 == 0
        assert AssetStock.objects.get(branch=bj3, item=other).在库数量 == 3
        _check_consistent()

    def test_multi_instance_line_reduces_qty(self, bj3):
        from unittest.mock import patch
        from apps.assets.management.commands.prod_data_fix_bj3_point import TARGET_NUMBER

        item = _item('BJ3P-I4')
        d = _doc(bj3, item, [(4, item)], 'CG20260806-025')
        target = FixedAsset.objects.filter(birth_line__transfer=d).first()

        with patch('apps.assets.management.commands.prod_data_fix_bj3_point.TARGET_NUMBER', target.内部编号):
            out = _run('--apply')
        assert '数量 4 → 3' in out
        assert d.lines.first().数量 == 3
        assert AssetStock.objects.get(branch=bj3, item=item).在库数量 == 3
        _check_consistent()

    def test_non_in_stock_rejects_and_missing_skips(self, bj3):
        from unittest.mock import patch
        from apps.assets.management.commands.prod_data_fix_bj3_point import TARGET_NUMBER
        item = _item('BJ3P-I5')
        d = _doc(bj3, item, [(1, item)], 'CG20260806-026')
        target = FixedAsset.objects.get(birth_line__transfer=d)
        target.当前状态 = '在用'
        target.save(update_fields=['当前状态'])
        with patch('apps.assets.management.commands.prod_data_fix_bj3_point.TARGET_NUMBER', target.内部编号):
            with pytest.raises(CommandError, match='非在库'):
                _run('--apply')
        # 目标不存在 → 幂等跳过（默认常量在测试库无匹配）
        out = _run()
        assert '不存在，无需处理' in out
