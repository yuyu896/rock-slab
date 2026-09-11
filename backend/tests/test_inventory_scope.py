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

    def test_create_ignores_department(self, authenticated_client, branch, other_branch_department):
        """部门维度退役：入参 department 被忽略（只读档案字段），创建成功且为空。"""
        resp = authenticated_client.post(INVENTORY_LIST_URL, {
            'name': '实例盘-全公司', 'branch': str(branch.id), 'kind': 'instance',
            'department': str(other_branch_department.id),
        }, format='json')
        assert resp.status_code == status.HTTP_201_CREATED
        task = InventoryTask.objects.get(name='实例盘-全公司')
        assert task.kind == 'instance'
        assert task.department is None
        assert task.is_instance_inventory is True

    def test_create_instance_kind_without_department(self, authenticated_client, branch):
        """kind=instance 即实例盘，无需部门。"""
        resp = authenticated_client.post(INVENTORY_LIST_URL, {
            'name': '实例盘-无部门', 'branch': str(branch.id), 'kind': 'instance',
        }, format='json')
        assert resp.status_code == status.HTTP_201_CREATED
        assert InventoryTask.objects.get(name='实例盘-无部门').is_instance_inventory is True

    def test_backfill_kind_from_department(self, branch, department):
        """存量回填口径：department 非空的老任务 is_instance 判定随 kind 迁移成立。"""
        legacy = InventoryTask.objects.create(
            name='老任务', branch=branch, department=department, kind='instance',
        )
        assert legacy.is_instance_inventory is True


@pytest.mark.django_db
class TestInstanceInventory:
    """实例盘（全分公司）：快照清单、逐台核对、漏盘规则、审批不改账。"""

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
        # 干扰项：在库实例不入清单；无部门在用实例 SI-001-8 属全公司口径应入清单
        FixedAsset.objects.create(
            item=item, 内部编号='SI-001-9', 当前状态='在库', branch=branch,
        )
        made.append(FixedAsset.objects.create(
            item=item, 内部编号='SI-001-8', 当前状态='在用',
            使用人='王五', branch=branch,
        ))
        return made

    def _make_task(self, branch, department=None, item=None, **kw):
        return InventoryTask.objects.create(
            name='实例盘', branch=branch, kind='instance',
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
        assert entries.count() == 4  # 全分公司在用实例（含无部门归属）
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
        self, authenticated_client, branch, second_branch, inst_item, department,
    ):
        from apps.assets.models import FixedAsset
        self._seed_instances(branch, inst_item, department)
        outsider = FixedAsset.objects.create(
            item=inst_item, 内部编号='SI-002-1', 当前状态='在用',
            使用人='赵六', branch=second_branch,  # 外分公司 → 不在清单
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
        assert missing == 2                              # 报告缺失明细来源（含无部门归属台）

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
        assert len(data['items']) == 4
        first = data['items'][0]
        assert {'instanceCode', 'assetName', 'holder', 'result'} <= set(first)
        assert data['progress']['totalItems'] == 4
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

    @staticmethod
    def _xlsx(headers, rows):
        import io
        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(headers)
        for r in rows:
            ws.append(r)
        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        buf.name = 'instance.xlsx'
        return buf

    def test_instance_template_and_import(
        self, authenticated_client, branch, inst_item, department,
    ):
        """实例盘 Excel 闭环：模板含清单快照；导入按内部编号回写 matched/missing。"""
        instances = self._seed_instances(branch, inst_item, department)
        task = self._make_task(branch, department)
        authenticated_client.post(_action('start', task.id))

        # 模板：表头含核对结果列，快照含跨部门/无部门全部在用实例
        resp = authenticated_client.get(_action('import-template', task.id))
        assert resp.status_code == status.HTTP_200_OK
        import openpyxl
        from io import BytesIO
        ws = openpyxl.load_workbook(BytesIO(resp.content)).active
        head = [c.value for c in ws[1]]
        assert head[:2] == ['序号', '内部编号'] and '核对结果' in head
        codes = {ws.cell(row=r, column=2).value for r in range(2, ws.max_row + 1)}
        assert codes == {i.内部编号 for i in instances}

        # 导入：2 已找到 / 1 未找到 / 1 非法值 / 1 不在清单
        headers = ['序号', '内部编号', '序列号', '品目编号', '品目名称', '使用人', '所属部门', '核对结果', '备注']
        rows = [
            [1, instances[0].内部编号, '', 'SCOPE-INST', '笔记本', '张三', '', '已找到', '线上核对'],
            [2, instances[1].内部编号, '', 'SCOPE-INST', '笔记本', '张三', '', '已找到', ''],
            [3, instances[2].内部编号, '', 'SCOPE-INST', '笔记本', '李四', '', '未找到', ''],
            [4, instances[3].内部编号, '', 'SCOPE-INST', '笔记本', '王五', '', '找到了', ''],
            [5, 'SI-999-9', '', 'SCOPE-INST', '笔记本', '赵六', '', '已找到', ''],
        ]
        resp = authenticated_client.post(
            _action('import-result', task.id), {'file': self._xlsx(headers, rows)}, format='multipart',
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()['imported'] == 3
        errors = resp.json()['errors']
        assert any('已找到/未找到' in e for e in errors)
        assert any('不在盘点范围' in e for e in errors)

        entries = {e.instance.内部编号: e for e in task.instance_items.select_related('instance')}
        assert entries[instances[0].内部编号].result == 'matched'
        assert entries[instances[0].内部编号].remarks == '线上核对'
        assert entries[instances[0].内部编号].check_count == 1
        assert entries[instances[0].内部编号].checked_by == entries[instances[0].内部编号].checked_by
        assert entries[instances[2].内部编号].result == 'missing'
        assert entries[instances[3].内部编号].result == 'unchecked'  # 非法值行未回写

    def test_instance_import_pending_rejected(self, authenticated_client, branch, inst_item, department):
        """pending 状态实例盘任务导入被拒。"""
        self._seed_instances(branch, inst_item, department)
        task = self._make_task(branch, department)
        headers = ['序号', '内部编号', '序列号', '品目编号', '品目名称', '使用人', '所属部门', '核对结果', '备注']
        resp = authenticated_client.post(
            _action('import-result', task.id),
            {'file': self._xlsx(headers, [[1, 'SI-001-1', '', '', '', '', '', '已找到', '']])},
            format='multipart',
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert '盘点中' in resp.json()['detail']

    def test_excel_endpoints_guarded_for_instance_task(
        self, authenticated_client, branch, inst_item, department,
    ):
        self._seed_instances(branch, inst_item, department)
        task = self._make_task(branch, department)
        authenticated_client.post(_action('start', task.id))
        assert authenticated_client.get(
            _action('import-template', task.id)).status_code == status.HTTP_200_OK
        assert authenticated_client.get(
            _action('export-report', task.id)).status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestStockBinRecycleRetired:
    """回收库库别已退役：创建携带 recycle 即拒。"""

    def test_create_with_recycle_bin_rejected(self, authenticated_client, branch):
        resp = authenticated_client.post(INVENTORY_LIST_URL, {
            'name': '回收库盘', 'branch': str(branch.id), 'stock_bin': 'recycle',
        }, format='json')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert '回收库' in str(resp.data)
