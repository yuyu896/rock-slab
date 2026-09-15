"""生产数据纠错命令测试：33分宁波按内部编号点删实例（多实例行数量联动）。"""
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


def _run(*args):
    out = StringIO()
    call_command('prod_data_fix_nb33', *args, stdout=out)
    return out.getvalue()


def _check_consistent():
    out = StringIO()
    call_command('check_ledger_consistency', stdout=out)
    return out.getvalue()


@pytest.fixture
def nb33(team):
    return Branch.objects.create(name='33分宁波', code='NB033', team=team)


def _multi_instance_doc(branch, item, qty, no):
    """多实例行采购单：一行 ×qty，出生 qty 个实例。"""
    t = Transfer.build(
        'purchase',
        {'调拨日期': datetime.date(2025, 6, 10), '审批状态': '已入库', '单据编号': no,
         '调入分公司': branch.name, '创建人': '测试'},
        所属分公司=branch,
    )
    t.save()
    TransferLine.objects.create(transfer=t, item=item, 行号=1, 数量=qty)
    ledger.apply_document(t)
    return Transfer.objects.get(pk=t.pk)


@pytest.mark.django_db
class TestNb33PointDelete:
    def test_point_delete_syncs_line_and_stock(self, nb33, second_branch):
        item = _item('NB33-I1')
        d1 = _multi_instance_doc(nb33, item, 6, 'CG20250610-004')
        d2 = _multi_instance_doc(nb33, item, 13, 'CG20250404-004')
        # 他分公司同品目基准
        _multi_instance_doc(second_branch, item, 5, 'CG20250404-099')

        from unittest.mock import patch
        from apps.assets.management.commands.prod_data_fix_nb33 import TARGET_NUMBERS
        born1 = sorted(FixedAsset.objects.filter(birth_line__transfer=d1).values_list('内部编号', flat=True))
        born2 = sorted(FixedAsset.objects.filter(birth_line__transfer=d2).values_list('内部编号', flat=True))
        targets = tuple(born1[-2:]) + (born2[0],)  # 行1 取 2 个、行2 取 1 个

        with patch('apps.assets.management.commands.prod_data_fix_nb33.TARGET_NUMBERS', targets):
            out = _run('--apply')

        assert '已写入：删 3 实例，2 行数量联动，台账在库 −3' in out
        row = AssetStock.objects.get(branch=nb33, item=item)
        assert row.在库数量 == 16  # 6+13−3
        assert FixedAsset.objects.filter(branch=nb33, item=item).count() == 16
        l1 = d1.lines.first(); l1.refresh_from_db()
        l2 = d2.lines.first(); l2.refresh_from_db()
        assert (l1.数量, l2.数量) == (4, 12)
        assert Transfer.objects.filter(pk__in=[d1.pk, d2.pk]).exists()  # 单据保留
        # 他分公司零波及
        assert AssetStock.objects.get(branch=second_branch, item=item).在库数量 == 5
        assert FixedAsset.objects.filter(branch=second_branch, item=item).count() == 5
        _check_consistent()

    def test_rejects_non_in_stock(self, nb33):
        item = _item('NB33-I2')
        d = _multi_instance_doc(nb33, item, 2, 'CG20250611-001')
        inst = FixedAsset.objects.filter(birth_line__transfer=d).first()
        inst.当前状态 = '在用'
        inst.save(update_fields=['当前状态'])

        from unittest.mock import patch
        from apps.assets.management.commands.prod_data_fix_nb33 import TARGET_NUMBERS
        targets = (inst.内部编号,)
        with patch('apps.assets.management.commands.prod_data_fix_nb33.TARGET_NUMBERS', targets):
            with pytest.raises(CommandError, match='非在库'):
                _run('--apply')
        assert FixedAsset.objects.filter(birth_line__transfer=d).count() == 2  # 零变更

    def test_rejects_line_qty_mismatch(self, nb33):
        item = _item('NB33-I3')
        d = _multi_instance_doc(nb33, item, 3, 'CG20250611-002')
        ln = d.lines.first()
        ln.数量 = 5  # 人为错位
        ln.save(update_fields=['数量'])

        from unittest.mock import patch
        from apps.assets.management.commands.prod_data_fix_nb33 import TARGET_NUMBERS
        targets = (FixedAsset.objects.filter(birth_line__transfer=d).first().内部编号,)
        with patch('apps.assets.management.commands.prod_data_fix_nb33.TARGET_NUMBERS', targets):
            with pytest.raises(CommandError, match='行账错位'):
                _run('--apply')

    def test_missing_target_skips(self, nb33):
        _multi_instance_doc(nb33, _item('NB33-I4'), 1, 'CG20250611-003')
        out = _run('--apply')  # 默认常量在测试库不存在 → 幂等跳过路径
        assert '全部不存在' in out
        assert FixedAsset.objects.filter(branch=nb33).count() == 1  # 零变更

    def test_dry_run_and_idempotent(self, nb33):
        item = _item('NB33-I5')
        d = _multi_instance_doc(nb33, item, 4, 'CG20250611-004')

        from unittest.mock import patch
        from apps.assets.management.commands.prod_data_fix_nb33 import TARGET_NUMBERS
        targets = tuple(sorted(FixedAsset.objects.filter(birth_line__transfer=d).values_list('内部编号', flat=True))[:1])
        with patch('apps.assets.management.commands.prod_data_fix_nb33.TARGET_NUMBERS', targets):
            out = _run()
            assert 'dry-run' in out
            assert FixedAsset.objects.filter(birth_line__transfer=d).count() == 4
            _run('--apply')
            out = _run('--apply')
            assert '全部不存在' in out
        _check_consistent()
