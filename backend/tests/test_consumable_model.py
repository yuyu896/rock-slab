"""消耗品模型测试（设计书 #2/5.2 三档，2026-08-27 修宪）：领用耗用发放 + 单据约束 + 存量迁移。"""
import pytest
from rest_framework import status

from apps.assets.models import AssetStock
from apps.assets.services import ledger
from apps.categories.models import Category


def _ensure_item(code, management_type='consumable', asset_category='低值易耗品类'):
    item, _ = Category.objects.get_or_create(
        asset_code=code,
        defaults={
            'asset_category': asset_category, 'item_category': '测试分类',
            'asset_name': f'品目 {code}', 'unit': '个',
            'management_type': management_type,
        },
    )
    return item


def _seed(branch, code, stock=10, in_use=0, recycle=0, management_type='consumable'):
    item = _ensure_item(code, management_type)
    if stock:
        ledger.apply_adjustment(branch, item, ledger.COLUMN_STOCK, stock, '造数')
    if in_use:
        ledger.apply_adjustment(branch, item, ledger.COLUMN_IN_USE, in_use, '造数')
    if recycle:
        ledger.apply_adjustment(branch, item, ledger.COLUMN_RECYCLE, recycle, '造数')
    return item


def _assign_payload(branch, lines, source='stock'):
    return {
        '调拨日期': '2026-08-27', '调出分公司': branch.name, '领用来源': source,
        'items': lines,
    }


@pytest.mark.django_db
class TestConsumableAssign:
    """消耗品领用 = 耗用发放：在库−N 总量降，不进在用。"""

    def test_assign_consumable_deducts_stock_only(self, authenticated_client, branch, item_id):
        from apps.organizations.models import Department
        dept = Department.objects.create(branch=branch, name='测试部')
        _seed(branch, 'CM-1', stock=10)
        resp = authenticated_client.post('/api/transfers/assign', _assign_payload(branch, [
            {'item': item_id('CM-1'), '数量': 3, '使用人': '张三', 'department': str(dept.id)},
        ]), format='json')
        assert resp.status_code == status.HTTP_201_CREATED, resp.data
        resp = authenticated_client.post(
            f"/api/transfers/{resp.data['id']}/approve", {'approved': True}, format='json')
        assert resp.status_code == 200
        row = AssetStock.objects.get(branch=branch, item__asset_code='CM-1')
        assert row.在库数量 == 7
        assert row.在用数量 == 0      # 不进在用
        assert row.总量 == 7          # 总量随耗用下降

    def test_mixed_lines_split_by_management_type(self, authenticated_client, branch, item_id):
        """混合单行级分流：消耗品行走耗用发放，数量行走 在库−N 在用+N。"""
        from apps.organizations.models import Department
        dept = Department.objects.create(branch=branch, name='测试部')
        _seed(branch, 'CM-2A', stock=10, management_type='consumable')
        _seed(branch, 'CM-2B', stock=10, management_type='quantity')
        resp = authenticated_client.post('/api/transfers/assign', _assign_payload(branch, [
            {'item': item_id('CM-2A'), '数量': 2, '使用人': '张三', 'department': str(dept.id)},
            {'item': item_id('CM-2B'), '数量': 4, '使用人': '李四', 'department': str(dept.id)},
        ]), format='json')
        assert resp.status_code == status.HTTP_201_CREATED, resp.data
        assert authenticated_client.post(
            f"/api/transfers/{resp.data['id']}/approve", {'approved': True}, format='json'
        ).status_code == 200
        a = AssetStock.objects.get(branch=branch, item__asset_code='CM-2A')
        b = AssetStock.objects.get(branch=branch, item__asset_code='CM-2B')
        assert (a.在库数量, a.在用数量) == (8, 0)
        assert (b.在库数量, b.在用数量) == (6, 4)

    def test_assign_recycle_bin_source_rejected(self, authenticated_client, branch, item_id):
        _seed(branch, 'CM-3', stock=5)
        resp = authenticated_client.post('/api/transfers/assign', _assign_payload(branch, [
            {'item': item_id('CM-3'), '数量': 1, '使用人': '张三', 'department': None},
        ], source='recycle_bin'), format='json')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert '消耗品无回收库存可领' in str(resp.data['detail'])


@pytest.mark.django_db
class TestConsumableDocConstraints:
    """消耗品单据约束：无回收、无可归还；采购/调拨正常。"""

    def test_recovery_rejected(self, authenticated_client, branch, item_id):
        _seed(branch, 'CM-4', stock=5)
        resp = authenticated_client.post('/api/transfers/recovery', {
            '调拨日期': '2026-08-27', '调出分公司': branch.name,
            'items': [{'item': item_id('CM-4'), '数量': 1}],
        }, format='json')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert '消耗品无回收' in str(resp.data['detail'])

    def test_return_rejected(self, authenticated_client, branch, item_id):
        _seed(branch, 'CM-5', stock=5)
        resp = authenticated_client.post('/api/transfers/return', {
            '调拨日期': '2026-08-27', '调入分公司': branch.name,
            'items': [{'item': item_id('CM-5'), '数量': 1}],
        }, format='json')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert '消耗品无可归还' in str(resp.data['detail'])

    def test_purchase_and_transfer_work(self, authenticated_client, branch, second_branch, item_id):
        _seed(branch, 'CM-6', stock=0)
        resp = authenticated_client.post('/api/transfers/purchase', {
            '调拨日期': '2026-08-27', '调入分公司': branch.name,
            'items': [{'item': item_id('CM-6'), '数量': 10}],
        }, format='json')
        assert resp.status_code == status.HTTP_201_CREATED, resp.data
        assert authenticated_client.post(
            f"/api/transfers/{resp.data['id']}/approve", {'approved': True}, format='json'
        ).status_code == 200
        assert AssetStock.objects.get(branch=branch, item__asset_code='CM-6').在库数量 == 10

        resp = authenticated_client.post('/api/transfers/transfer', {
            '调拨日期': '2026-08-27', '调出分公司': branch.name, '调入分公司': second_branch.name,
            'items': [{'item': item_id('CM-6'), '数量': 4}],
        }, format='json')
        assert resp.status_code == status.HTTP_201_CREATED, resp.data
        assert authenticated_client.post(
            f"/api/transfers/{resp.data['id']}/approve", {'approved': True}, format='json'
        ).status_code == 200
        assert AssetStock.objects.get(branch=branch, item__asset_code='CM-6').在库数量 == 6
        assert AssetStock.objects.get(branch=second_branch, item__asset_code='CM-6').在库数量 == 4


@pytest.mark.django_db
class TestMigrateConsumablesCommand:
    """存量 B 类迁移：dry-run 预览、apply 只迁双零、对账等价。"""

    def _run(self, *args):
        from io import StringIO
        from django.core.management import call_command
        out = StringIO()
        call_command('migrate_consumables', *args, stdout=out)
        return out.getvalue()

    def test_dry_run_does_not_write(self, branch):
        _seed(branch, 'MG-1', stock=5, management_type='quantity')
        out = self._run()
        assert 'MG-1' in out and 'dry-run' in out
        assert Category.objects.get(asset_code='MG-1').management_type == 'quantity'

    def test_apply_migrates_double_zero_only(self, branch, second_branch):
        ok = _seed(branch, 'MG-2', stock=5, management_type='quantity')
        _seed(second_branch, 'MG-3', stock=3, in_use=2, management_type='quantity')
        _seed(branch, 'MG-4', stock=3, recycle=1, management_type='quantity')
        _ensure_item('MG-5', management_type='instance')

        out = self._run('--apply')
        ok.refresh_from_db()
        assert ok.management_type == 'consumable'
        assert '迁移 1 项' in out
        assert '[跳过] MG-3' in out and '[跳过] MG-4' in out
        assert '[人工] MG-5' in out
        for code in ('MG-3', 'MG-4'):
            assert Category.objects.get(asset_code=code).management_type == 'quantity'

    def test_migration_keeps_ledger_consistent(self, branch):
        """在用=0 迁移后对账零差异（新旧矩阵重放等价）。"""
        _seed(branch, 'MG-6', stock=7, management_type='quantity')
        self._run('--apply')
        from django.core.management import call_command
        from io import StringIO
        out = StringIO()
        call_command('check_ledger_consistency', stdout=out)
        assert '零差异' in out.getvalue()
