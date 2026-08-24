"""实例档案（P2 第二刀）：冻结只读 + 序列号补录 + 生平查询 + 待补录筛选。

对应 fixed-asset-instance / document-instance-binding 能力。
"""
import datetime

import pytest
from conftest import _client_for

from apps.assets.views import FixedAssetViewSet

FA_EXPORT_HEADERS = FixedAssetViewSet.FA_EXPORT_HEADERS


def _grant(user, code):
    from apps.permissions.models import OperationGrant
    OperationGrant.objects.get_or_create(user=user, code=code)
    return user


@pytest.fixture
def item_instance(branch):
    from apps.categories.models import Category
    return Category.objects.create(
        asset_category='固定', item_category='办公',
        asset_name='ThinkPad T14', asset_code='NB-001', unit='台',
        management_type='instance',
    )


@pytest.fixture
def inst(branch, item_instance):
    from apps.assets.models import FixedAsset
    return FixedAsset.objects.create(
        item=item_instance, 内部编号='NB-001-1',
        当前状态='在库', branch=branch, 入库日期=datetime.date(2026, 8, 24),
    )


def _purchase_doc(branch, item, qty=1):
    """造一张已生效采购单 + 明细行（实例出生的合规路径）。"""
    from apps.transfers.models import Transfer, TransferLine
    transfer = Transfer.objects.create(
        单据编号='CG20260824-001', 调拨日期=datetime.date(2026, 8, 24),
        调出分公司=branch.name, from_branch=branch, to_branch=branch,
        action_type='purchase', 审批状态='已入库', 供应商='联想',
    )
    return TransferLine.objects.create(
        transfer=transfer, item=item, 行号=1, 数量=qty, 单价=7999,
    )


@pytest.mark.django_db
class TestFrozenWriteEndpoints:
    def test_create_frozen(self, supervisor_user):
        client = _client_for(supervisor_user)
        resp = client.post('/api/assets/fixed-assets', {'内部编号': 'X-1'})
        assert resp.status_code == 405
        assert '流转单' in resp.data['detail']

    def test_update_frozen(self, supervisor_user, inst):
        client = _client_for(supervisor_user)
        resp = client.patch(f'/api/assets/fixed-assets/{inst.pk}', {'使用人': '张三'})
        assert resp.status_code == 405

    def test_destroy_frozen(self, supervisor_user, inst):
        client = _client_for(supervisor_user)
        resp = client.delete(f'/api/assets/fixed-assets/{inst.pk}')
        assert resp.status_code == 405

    def test_batch_delete_frozen(self, supervisor_user, inst):
        client = _client_for(supervisor_user)
        resp = client.post('/api/assets/fixed-assets/batch-delete', {'ids': [str(inst.pk)]})
        assert resp.status_code == 405
        from apps.assets.models import FixedAsset
        assert FixedAsset.objects.filter(pk=inst.pk).exists()

    def test_import_gone(self, supervisor_user):
        client = _client_for(supervisor_user)
        resp = client.post('/api/assets/fixed-assets/import')
        assert resp.status_code == 410


@pytest.mark.django_db
class TestInstanceListOutput:
    def test_list_joins_dictionary_and_birth(self, supervisor_user, branch, inst):
        line = _purchase_doc(branch, inst.item)
        inst.birth_line = line
        inst.save(update_fields=['birth_line'])

        client = _client_for(supervisor_user)
        resp = client.get('/api/assets/fixed-assets')
        assert resp.status_code == 200
        data = resp.data['results'][0]
        assert data['item_code'] == 'NB-001'
        assert data['item_name'] == 'ThinkPad T14'
        assert data['management_type'] == 'instance'
        assert data['待补录'] is True          # 序列号为空
        assert data['供应商'] == '联想'         # 出生行派生
        assert str(data['单价']) == '7999.00'
        assert str(data['采购日期']) == '2026-08-24'

    def test_pending_serial_filter(self, supervisor_user, inst):
        from apps.assets.models import FixedAsset
        FixedAsset.objects.create(
            item=inst.item, 内部编号='NB-001-2', 当前状态='在库',
            branch=inst.branch, 序列号='SN-XYZ',
        )
        client = _client_for(supervisor_user)
        resp = client.get('/api/assets/fixed-assets?pending_serial=1')
        assert resp.data['count'] == 1
        assert resp.data['results'][0]['内部编号'] == 'NB-001-1'

    def test_export_headers(self, supervisor_user, inst):
        client = _client_for(supervisor_user)
        resp = client.get('/api/assets/fixed-assets/export')
        assert resp.status_code == 200
        assert FA_EXPORT_HEADERS[0] == '序号'
        assert '品目编号' in FA_EXPORT_HEADERS
        assert '电脑序列号' not in FA_EXPORT_HEADERS


@pytest.mark.django_db
class TestSupplement:
    def test_supplement_with_manage_instances(self, supervisor_user, inst):
        _grant(supervisor_user, 'manage_instances')
        client = _client_for(supervisor_user)
        resp = client.patch(
            f'/api/assets/fixed-assets/{inst.pk}/supplement',
            {'序列号': 'SN-123', '备注': '首批'},
        )
        assert resp.status_code == 200
        inst.refresh_from_db()
        assert inst.序列号 == 'SN-123'
        assert inst.备注 == '首批'
        assert resp.data['待补录'] is False

    def test_supplement_rejects_state_fields(self, supervisor_user, inst):
        _grant(supervisor_user, 'manage_instances')
        client = _client_for(supervisor_user)
        resp = client.patch(
            f'/api/assets/fixed-assets/{inst.pk}/supplement',
            {'序列号': 'SN-123', '当前状态': '在用'},
        )
        assert resp.status_code == 400

    def test_supplement_denied_without_operation(self, supervisor_user, inst):
        client = _client_for(supervisor_user)
        resp = client.patch(
            f'/api/assets/fixed-assets/{inst.pk}/supplement',
            {'序列号': 'SN-123'},
        )
        assert resp.status_code == 403


@pytest.mark.django_db
class TestTimeline:
    def test_timeline_covers_birth_and_flows(self, supervisor_user, branch, inst):
        from apps.transfers.models import Transfer, TransferLineInstance
        line = _purchase_doc(branch, inst.item)
        inst.birth_line = line
        inst.save(update_fields=['birth_line'])
        TransferLineInstance.objects.create(line=line, instance=inst)

        assign = Transfer.objects.create(
            单据编号='LY20260824-001', 调拨日期=datetime.date(2026, 8, 24),
            调出分公司=branch.name, from_branch=branch,
            action_type='assign', 审批状态='已通过',
        )
        assign_line = assign.lines.create(
            item=inst.item, 行号=1, 数量=1, 使用人='张三',
        )
        TransferLineInstance.objects.create(line=assign_line, instance=inst)

        client = _client_for(supervisor_user)
        resp = client.get(f'/api/assets/fixed-assets/{inst.pk}/timeline')
        assert resp.status_code == 200
        assert resp.data['birth']['供应商'] == '联想'
        assert resp.data['birth']['单据编号'] == 'CG20260824-001'
        actions = [row['action_type'] for row in resp.data['timeline']]
        assert actions == ['assign', 'purchase']  # 倒序
        assert resp.data['timeline'][0]['使用人'] == '张三'
