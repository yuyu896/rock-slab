"""purge_business_data 命令契约：清业务数据、留字典/组织/用户；清后对账通过、管理方式解锁。"""
import pytest
from django.core.management import call_command
from io import StringIO

from apps.assets.models import AssetStock, FixedAsset, InstanceSequence, LedgerAdjustment
from apps.assets.services import ledger
from apps.audit.models import AuditLog
from apps.categories.models import Category
from apps.categories.serializers import CategorySerializer
from apps.inventories.models import InventoryTask
from apps.notifications.models import Notification
from apps.transfers.models import DocumentSequence, Transfer, TransferLine, TransferLineInstance

BUSINESS_MODELS = [
    Notification, InventoryTask, FixedAsset, TransferLineInstance,
    TransferLine, Transfer, LedgerAdjustment, AssetStock, InstanceSequence,
    DocumentSequence, AuditLog,
]


def _run(apply=False):
    out = StringIO()
    call_command('purge_business_data', *(['--apply'] if apply else []), stdout=out)
    return out.getvalue()


def _check():
    out = StringIO()
    try:
        call_command('check_ledger_consistency', stdout=out)
        return 0, out.getvalue()
    except SystemExit as e:
        return e.code, out.getvalue()


def _seed(branch, admin_user):
    item, _ = Category.objects.get_or_create(
        asset_code='PURGE-001',
        defaults={'asset_category': '测试类目', 'item_category': '测试分类',
                  'asset_name': '清理样例', 'unit': '个'},
    )
    ledger.apply_adjustment(branch, item, ledger.COLUMN_STOCK, 5, '测试造数')
    transfer = Transfer.objects.create(
        调拨日期='2026-08-01', 调出分公司=branch.name, from_branch=branch,
        action_type='purchase', 审批状态='已入库',
    )
    line = TransferLine.objects.create(transfer=transfer, item=item, 行号=1, 数量=5)
    fa = FixedAsset.objects.create(item=item, 内部编号='PURGE-INS-001', birth_line=line)
    TransferLineInstance.objects.create(line=line, instance=fa)
    InventoryTask.objects.create(name='清理盘点样例', branch=branch)
    Notification.objects.create(recipient=admin_user, notification_type='system', title='t', content='c')
    AuditLog.objects.create(action='create', resource_type='Transfer')
    DocumentSequence.objects.create(action_type='purchase', date='2026-08-01', last_no=9)
    InstanceSequence.objects.create(item=item, last_no=9)


@pytest.mark.django_db
class TestPurgeBusinessData:
    def test_dry_run_keeps_data(self, branch, admin_user):
        _seed(branch, admin_user)
        text = _run()
        assert '预演' in text
        assert Transfer.objects.exists()
        assert AssetStock.objects.filter(在库数量=5).exists()

    def test_apply_clears_business_keeps_dictionary_and_org(self, branch, admin_user):
        _seed(branch, admin_user)
        text = _run(apply=True)
        for model in BUSINESS_MODELS:
            assert not model.objects.exists(), model.__name__
        assert Category.objects.filter(asset_code='PURGE-001').exists()
        branch.refresh_from_db()

    def test_apply_then_ledger_consistent(self, branch, admin_user):
        _seed(branch, admin_user)
        _run(apply=True)
        code, text = _check()
        assert code == 0

    def test_apply_unlocks_management_type_switch(self, branch, admin_user):
        """清空后品目无存量无档案，数量→实例切换放行（本次清理的目标）。"""
        _seed(branch, admin_user)
        _run(apply=True)
        item = Category.objects.get(asset_code='PURGE-001')
        serializer = CategorySerializer(item, data={'management_type': 'instance'}, partial=True)
        assert serializer.is_valid(), serializer.errors
        serializer.save()
        item.refresh_from_db()
        assert item.management_type == 'instance'
