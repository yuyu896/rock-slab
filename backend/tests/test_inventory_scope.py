"""盘点范围模型测试（设计书十三节）：库别维度台账盘 + 部门实例盘（差异不自动改账）。"""
import pytest
from rest_framework import status

from apps.assets.services import ledger as ledger
from apps.categories.models import Category
from apps.organizations.models import Department
from apps.inventories.models import InventoryTask, InventoryInstanceItem

INVENTORY_LIST_URL = '/api/inventories/'


def _action(action_name, pk):
    return f'/api/inventories/{pk}/{action_name}'


@pytest.fixture
def qty_item(db):
    return Category.objects.create(
        asset_category='数量类目', item_category='办公耗材',
        asset_name='打印纸', asset_code='SCOPE-QTY', unit='包',
        management_type='quantity',
    )


@pytest.fixture
def inst_item(db):
    return Category.objects.create(
        asset_category='实例类目', item_category='电子设备',
        asset_name='笔记本', asset_code='SCOPE-INST', unit='台',
        management_type='instance',
    )


@pytest.fixture
def department(db, branch):
    return Department.objects.create(branch=branch, name='行政部')


@pytest.fixture
def other_branch_department(db, second_branch):
    return Department.objects.create(branch=second_branch, name='其他分公司部门')


@pytest.mark.django_db
class TestStockBinInventory:
    """库别维度：应盘取对应列、差异调整单修对应列。"""

    def _seed_stock(self, branch, item):
        ledger.apply_adjustment(branch, item, ledger.COLUMN_STOCK, 5, '造数')
        ledger.apply_adjustment(branch, item, ledger.COLUMN_RECYCLE, 2, '造数')
        ledger.apply_adjustment(branch, item, ledger.COLUMN_IN_USE, 3, '造数')

    def test_recycle_bin_task_expected_from_recycle_column(
        self, authenticated_client, branch, qty_item,
    ):
        self._seed_stock(branch, qty_item)
        task = InventoryTask.objects.create(
            name='回收库盘', branch=branch, stock_bin='recycle', created_by=None,
        )
        resp = authenticated_client.post(_action('start', task.id))
        assert resp.status_code == status.HTTP_200_OK

        from apps.assets.models import AssetStock
        stock = AssetStock.objects.get(branch=branch, item=qty_item)
        items = task.items.all()
        assert items.count() == 1
        assert items.first().expected_qty == 2  # 回收库列
        assert items.first().stock_id == stock.id

    def test_stock_bin_task_skips_zero_column_rows(self, authenticated_client, branch, qty_item):
        # 在库 0、回收库 2：在库盘跳过；回收库盘纳入
        ledger.apply_adjustment(branch, qty_item, ledger.COLUMN_RECYCLE, 2, '造数')
        stock_task = InventoryTask.objects.create(
            name='在库盘', branch=branch, stock_bin='stock',
        )
        authenticated_client.post(_action('start', stock_task.id))
        assert stock_task.items.count() == 0  # 在库列=0，跳过

    def test_recycle_variance_adjusts_recycle_column_only(
        self, authenticated_client, branch, qty_item, admin_user,
    ):
        from apps.assets.models import AssetStock
        self._seed_stock(branch, qty_item)
        task = InventoryTask.objects.create(
            name='回收库盘差异', branch=branch, stock_bin='recycle', missed_rule='keep',
        )
        authenticated_client.post(_action('start', task.id))
        stock = AssetStock.objects.get(branch=branch, item=qty_item)

        resp = authenticated_client.post(_action('check', task.id), {
            'stock_id': str(stock.id), 'qty': 0,
        })
        assert resp.status_code == status.HTTP_200_OK
        authenticated_client.post(_action('submit', task.id))
        resp = authenticated_client.post(_action('approve', task.id))
        assert resp.status_code == status.HTTP_200_OK

        stock.refresh_from_db()
        assert stock.回收库数量 == 0   # 修回收库列
        assert stock.在库数量 == 5    # 在库列不动
        adj = task.adjustments.get()
        assert adj.目标列 == '回收库数量'
        assert adj.变动量 == -2
        assert '回收库' in adj.事由

    def test_serializer_rejects_department_outside_branch(
        self, authenticated_client, branch, other_branch_department,
    ):
        resp = authenticated_client.post(INVENTORY_LIST_URL, {
            'name': '跨部门', 'branch': str(branch.id),
            'department': str(other_branch_department.id),
        }, format='json')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert 'department' in resp.json()


@pytest.mark.django_db
class TestInstanceInventory:
    """部门实例盘：快照清单、逐台核对、漏盘规则、审批不改账。"""

    def _seed_instances(self, branch, item, department):
        from apps.assets.models import FixedAsset
        made = []
        for i, (code, holder) in enumerate([
            ('SI-001-1', '张三'), ('SI-001-2', '张三'), ('SI-001-3', '李四'),
        ]):
            made.append(FixedAsset.objects.create(
                item=item, 内部编号=code, 当前状态='在用',
                使用人=holder, department=department, branch=branch,
            ))
        # 干扰项：在库实例 / 其他部门实例 / 数量品目台账（均不应入清单）
        FixedAsset.objects.create(
            item=item, 内部编号='SI-001-9', 当前状态='在库', branch=branch,
        )
        FixedAsset.objects.create(
            item=item, 内部编号='SI-001-8', 当前状态='在用',
            使用人='王五', branch=branch,  # 无部门
        )
        return made

    def _make_task(self, branch, department, item=None, **kw):
        return InventoryTask.objects.create(
            name='部门实例盘', branch=branch, department=department,
            missed_rule=kw.pop('missed_rule', 'keep'), **kw,
        )

    def test_start_generates_instance_snapshot(
        self, authenticated_client, branch, inst_item, department,
    ):
        instances = self._seed_instances(branch, inst_item, department)
        ledger.apply_adjustment(branch, inst_item, ledger.COLUMN_IN_USE, 5, '造数')
        task = self._make_task(branch, department)

        resp = authenticated_client.post(_action('start', task.id))
        assert resp.status_code == status.HTTP_200_OK
        assert task.is_instance_inventory is True
        entries = task.instance_items.all()
        assert entries.count() == 3  # 仅部门内在用实例
        assert set(entries.values_list('instance_id', flat=True)) == {
            i.id for i in instances
        }
        assert task.items.count() == 0  # 不生成数量盘点项

    def test_check_instance_found_and_missing(
        self, authenticated_client, branch, inst_item, department,
    ):
        instances = self._seed_instances(branch, inst_item, department)
        task = self._make_task(branch, department)
        authenticated_client.post(_action('start', task.id))

        r1 = authenticated_client.post(_action('check-instance', task.id), {
            'instanceId': str(instances[0].id), 'found': True,
        }, format='json')
        r2 = authenticated_client.post(_action('check-instance', task.id), {
            'instanceId': str(instances[1].id), 'found': False, 'remarks': '工位未找到',
        }, format='json')
        assert r1.status_code == status.HTTP_200_OK
        assert r2.status_code == status.HTTP_200_OK
        assert r1.json()['result'] == 'matched'
        assert r2.json()['result'] == 'missing'

        # 重复核对以最后一次为准，次数累计
        r3 = authenticated_client.post(_action('check-instance', task.id), {
            'instanceId': str(instances[1].id), 'found': True,
        }, format='json')
        assert r3.json()['result'] == 'matched'
        assert r3.json()['checkCount'] == 2

    def test_check_instance_rejects_foreign_instance(
        self, authenticated_client, branch, inst_item, department,
    ):
        from apps.assets.models import FixedAsset
        self._seed_instances(branch, inst_item, department)
        outsider = FixedAsset.objects.create(
            item=inst_item, 内部编号='SI-002-1', 当前状态='在用',
            使用人='赵六', branch=branch,  # 无部门 → 不在清单
        )
        task = self._make_task(branch, department)
        authenticated_client.post(_action('start', task.id))
        resp = authenticated_client.post(_action('check-instance', task.id), {
            'instanceId': str(outsider.id), 'found': True,
        }, format='json')
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_submit_missed_zero_marks_missing(
        self, authenticated_client, branch, inst_item, department,
    ):
        self._seed_instances(branch, inst_item, department)
        task = self._make_task(branch, department, missed_rule='zero')
        authenticated_client.post(_action('start', task.id))
        entries = task.instance_items.all()
        authenticated_client.post(_action('check-instance', task.id), {
            'instanceId': str(entries.first().instance_id), 'found': True,
        }, format='json')
        authenticated_client.post(_action('submit', task.id))
        results = set(task.instance_items.values_list('result', flat=True))
        assert results == {'matched', 'missing'}  # 未核对 2 台归缺失

    def test_approve_no_adjustment_no_ledger_change(
        self, authenticated_client, branch, inst_item, department,
    ):
        from apps.assets.models import AssetStock
        self._seed_instances(branch, inst_item, department)
        ledger.apply_adjustment(branch, inst_item, ledger.COLUMN_IN_USE, 3, '造数')
        task = self._make_task(branch, department, missed_rule='zero')
        authenticated_client.post(_action('start', task.id))
        for entry in task.instance_items.all()[:2]:
            authenticated_client.post(_action('check-instance', task.id), {
                'instanceId': str(entry.instance_id), 'found': True,
            }, format='json')
        authenticated_client.post(_action('submit', task.id))
        resp = authenticated_client.post(_action('approve', task.id))
        assert resp.status_code == status.HTTP_200_OK

        task.refresh_from_db()
        assert task.status == 'completed'
        assert task.adjustments.count() == 0            # 不自动改账
        stock = AssetStock.objects.get(branch=branch, item=inst_item)
        assert stock.在用数量 == 3                       # 台账零变化
        missing = task.instance_items.filter(result='missing').count()
        assert missing == 1                              # 报告缺失明细来源

    def test_report_returns_instance_items(
        self, authenticated_client, branch, inst_item, department,
    ):
        self._seed_instances(branch, inst_item, department)
        task = self._make_task(branch, department, missed_rule='zero')
        authenticated_client.post(_action('start', task.id))
        authenticated_client.post(_action('submit', task.id))

        resp = authenticated_client.get(_action('report', task.id))
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data['task']['inventoryKind'] == 'instance'
        assert len(data['items']) == 3
        first = data['items'][0]
        assert {'instanceCode', 'assetName', 'holder', 'result'} <= set(first)
        assert data['progress']['totalItems'] == 3
        assert data['adjustments'] == {'total': 0, 'surplus': 0, 'missing': 0}

    def test_stock_actions_rejected_on_instance_task(
        self, authenticated_client, branch, inst_item, department,
    ):
        self._seed_instances(branch, inst_item, department)
        task = self._make_task(branch, department)
        authenticated_client.post(_action('start', task.id))
        resp = authenticated_client.post(_action('check', task.id), {
            'stockId': '00000000-0000-0000-0000-000000000000', 'qty': 1,
        }, format='json')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

        resp = authenticated_client.post(_action('check-instance', task.id), {
            'instanceId': '00000000-0000-0000-0000-000000000000', 'found': True,
        }, format='json')
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_check_instance_rejected_on_stock_task(
        self, authenticated_client, branch, qty_item,
    ):
        task = InventoryTask.objects.create(name='台账盘', branch=branch)
        resp = authenticated_client.post(_action('check-instance', task.id), {
            'instanceId': '00000000-0000-0000-0000-000000000000', 'found': True,
        }, format='json')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_excel_endpoints_guarded_for_instance_task(
        self, authenticated_client, branch, inst_item, department,
    ):
        self._seed_instances(branch, inst_item, department)
        task = self._make_task(branch, department)
        authenticated_client.post(_action('start', task.id))
        assert authenticated_client.get(
            _action('import-template', task.id)).status_code == status.HTTP_400_BAD_REQUEST
        assert authenticated_client.get(
            _action('export-report', task.id)).status_code == status.HTTP_200_OK
