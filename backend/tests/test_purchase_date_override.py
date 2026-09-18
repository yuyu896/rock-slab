"""采购日期个体覆盖（purchase-date-override）测试：序列化器链 / timeline 链 / 填充命令。"""
import datetime
import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from io import StringIO

from apps.assets.models import FixedAsset
from apps.assets.serializers import FixedAssetSerializer
from apps.assets.services import ledger
from apps.categories.models import Category
from apps.organizations.models import Branch
from apps.transfers.models import Transfer, TransferLine
from apps.users.models import User


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


def _purchase(branch, item, qty, no, date):
    t = Transfer.build(
        'purchase',
        {'调拨日期': date, '审批状态': '已入库', '单据编号': no,
         '调入分公司': branch.name, '创建人': '测试'},
        所属分公司=branch,
    )
    t.save()
    TransferLine.objects.create(transfer=t, item=item, 行号=1, 数量=qty)
    ledger.apply_document(t)
    return Transfer.objects.get(pk=t.pk)


@pytest.fixture
def qz2(team):
    return Branch.objects.create(name='泉州二分', code='QZ002', team=team)


@pytest.mark.django_db
class TestSerializerChain:
    def test_override_wins_and_empty_falls_back(self, qz2):
        item = _item('PDO-I1')
        _purchase(qz2, item, 3, 'CG20250723-004', datetime.date(2025, 7, 23))
        a, b, c = FixedAsset.objects.filter(branch=qz2).order_by('内部编号')
        a.采购日期 = datetime.date(2025, 12, 5)
        a.save(update_fields=['采购日期'])

        data = FixedAssetSerializer(a).data
        # 类型混合：MethodField 透传 date 对象；模型 DateField 序列化为 ISO 字符串
        assert data['采购日期'] == datetime.date(2025, 12, 5)  # 覆盖生效
        assert data['入库日期'] == '2025-07-23'                 # 快照不动
        for x in (b, c):
            assert FixedAssetSerializer(x).data['采购日期'] == datetime.date(2025, 7, 23)  # 空回落批次

    def test_no_birth_line_with_and_without_override(self, qz2):
        item = _item('PDO-I2')
        inst = FixedAsset.objects.create(
            item=item, 内部编号='PDO-I2-X-1', 当前状态='在库', branch=qz2,
        )
        assert FixedAssetSerializer(inst).data['采购日期'] is None  # 无出生行无覆盖
        inst.采购日期 = datetime.date(2025, 1, 6)
        inst.save(update_fields=['采购日期'])
        assert FixedAssetSerializer(inst).data['采购日期'] == datetime.date(2025, 1, 6)  # 覆盖仍生效


@pytest.mark.django_db
class TestTimelineChain:
    def test_timeline_purchase_date_uses_override_doc_date_untouched(self, qz2, staff_client):
        from apps.permissions.models import OperationGrant, ManagementScope
        user = User.objects.get(phone='13900000004')
        ManagementScope.objects.create(user=user, branch=qz2)
        item = _item('PDO-I3')
        _purchase(qz2, item, 1, 'CG20250723-005', datetime.date(2025, 7, 23))
        inst = FixedAsset.objects.get(branch=qz2)
        inst.采购日期 = datetime.date(2025, 5, 7)
        inst.save(update_fields=['采购日期'])

        resp = staff_client.get(f'/api/assets/fixed-assets/{inst.id}/timeline')
        assert resp.status_code == 200
        birth = resp.data['birth']
        assert birth['采购日期'] == datetime.date(2025, 5, 7)   # 覆盖生效
        assert birth['日期'] == datetime.date(2025, 7, 23)      # 单据日期原样


@pytest.mark.django_db
class TestFillCommand:
    def _targets(self):
        from apps.assets.management.commands.prod_data_fix_qz2_purchase_dates import TARGET_DATES
        return TARGET_DATES

    def test_fill_override(self, qz2):
        from unittest.mock import patch
        item = _item('PDO-I4')
        _purchase(qz2, item, 3, 'CG20250723-006', datetime.date(2025, 7, 23))
        nos = list(FixedAsset.objects.filter(branch=qz2).order_by('内部编号').values_list('内部编号', flat=True))
        targets = {nos[0]: datetime.date(2025, 7, 25), nos[1]: datetime.date(2025, 12, 5)}

        out = StringIO()
        with patch('apps.assets.management.commands.prod_data_fix_qz2_purchase_dates.TARGET_DATES', targets):
            call_command('prod_data_fix_qz2_purchase_dates', '--apply', stdout=out)
        assert '已写入：2 条采购日期覆盖' in out.getvalue()
        assert FixedAsset.objects.get(内部编号=nos[0]).采购日期 == datetime.date(2025, 7, 25)
        assert FixedAsset.objects.get(内部编号=nos[1]).采购日期 == datetime.date(2025, 12, 5)
        assert FixedAsset.objects.get(内部编号=nos[2]).采购日期 is None  # 未列入不动

    def test_missing_aborts_and_idempotent(self, qz2):
        from unittest.mock import patch
        item = _item('PDO-I5')
        _purchase(qz2, item, 1, 'CG20250723-007', datetime.date(2025, 7, 23))
        real = FixedAsset.objects.get(branch=qz2).内部编号
        targets = {real: datetime.date(2025, 8, 1), 'A-a00007-QZ002-99': datetime.date(2025, 8, 1)}

        with patch('apps.assets.management.commands.prod_data_fix_qz2_purchase_dates.TARGET_DATES', targets):
            with pytest.raises(CommandError, match='缺失'):
                call_command('prod_data_fix_qz2_purchase_dates', '--apply', stdout=StringIO())
        assert FixedAsset.objects.get(内部编号=real).采购日期 is None  # 零变更

        with patch('apps.assets.management.commands.prod_data_fix_qz2_purchase_dates.TARGET_DATES', {real: datetime.date(2025, 8, 1)}):
            out = StringIO()
            call_command('prod_data_fix_qz2_purchase_dates', '--apply', stdout=out)
            out2 = StringIO()
            call_command('prod_data_fix_qz2_purchase_dates', '--apply', stdout=out2)
        assert '实际写入 1 条' in out.getvalue()
        assert '实际写入 0 条' in out2.getvalue()  # 幂等
