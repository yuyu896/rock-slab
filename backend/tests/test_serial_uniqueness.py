"""serial-uniqueness：补录部分更新+全局查重；重复报告命令。"""
import pytest
from rest_framework import status

from apps.assets.models import FixedAsset
from apps.categories.models import Category


def _item(code):
    item, _ = Category.objects.get_or_create(
        asset_code=code,
        defaults={'asset_category': '序列测试', 'item_category': '电脑',
                  'asset_name': f'品目 {code}', 'unit': '台', 'management_type': 'instance'},
    )
    return item


def _inst(branch, item, no, serial=''):
    code = branch.code if branch else 'NOBR'
    return FixedAsset.objects.create(
        item=item, 内部编号=f'{item.asset_code}-{code}-{no}',
        当前状态='在库', branch=branch, 序列号=serial,
    )


def _grant(user, code='manage_instances'):
    from apps.permissions.models import OperationGrant
    OperationGrant.objects.get_or_create(user=user, code=code)


@pytest.mark.django_db
class TestSupplementUniqueness:
    def test_second_supplement_same_serial_rejected(self, manager_user, branch):
        from conftest import _client_for
        _grant(manager_user)
        item = _item('SN-UQ-1')
        a = _inst(branch, item, 1, serial='SN-ABC-001')
        b = _inst(branch, item, 2)
        client = _client_for(manager_user)
        resp = client.patch(f'/api/assets/fixed-assets/{b.id}/supplement',
                            {'序列号': 'SN-ABC-001'}, format='json')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert 'SN-ABC-001' in str(resp.data['序列号'])
        b.refresh_from_db()
        assert b.序列号 == ''
        a.refresh_from_db()
        assert a.序列号 == 'SN-ABC-001'

    def test_unique_serial_accepted(self, manager_user, branch):
        from conftest import _client_for
        _grant(manager_user)
        item = _item('SN-UQ-2')
        a = _inst(branch, item, 1, serial='SN-ABC-001')
        b = _inst(branch, item, 2)
        resp = _client_for(manager_user).patch(
            f'/api/assets/fixed-assets/{b.id}/supplement',
            {'序列号': 'SN-ABC-002'}, format='json')
        assert resp.status_code == status.HTTP_200_OK
        b.refresh_from_db()
        assert b.序列号 == 'SN-ABC-002'

    def test_remark_only_keeps_serial(self, manager_user, branch):
        from conftest import _client_for
        _grant(manager_user)
        item = _item('SN-UQ-3')
        inst = _inst(branch, item, 1, serial='SN-KEEP-001')
        resp = _client_for(manager_user).patch(
            f'/api/assets/fixed-assets/{inst.id}/supplement',
            {'备注': '只改备注'}, format='json')
        assert resp.status_code == status.HTTP_200_OK
        inst.refresh_from_db()
        assert inst.序列号 == 'SN-KEEP-001'
        assert inst.备注 == '只改备注'

    def test_explicit_empty_serial_returns_to_pending(self, manager_user, branch):
        from conftest import _client_for
        _grant(manager_user)
        item = _item('SN-UQ-4')
        inst = _inst(branch, item, 1, serial='SN-OLD-001')
        resp = _client_for(manager_user).patch(
            f'/api/assets/fixed-assets/{inst.id}/supplement',
            {'序列号': ''}, format='json')
        assert resp.status_code == status.HTTP_200_OK
        inst.refresh_from_db()
        assert inst.序列号 == ''

    def test_supplement_own_serial_unchanged_ok(self, manager_user, branch):
        """重提交自身已有序列号（值未变）不构成重复。"""
        from conftest import _client_for
        _grant(manager_user)
        item = _item('SN-UQ-5')
        inst = _inst(branch, item, 1, serial='SN-SELF-001')
        resp = _client_for(manager_user).patch(
            f'/api/assets/fixed-assets/{inst.id}/supplement',
            {'序列号': 'SN-SELF-001', '备注': '改备注连带原序列号'}, format='json')
        assert resp.status_code == status.HTTP_200_OK
        inst.refresh_from_db()
        assert inst.序列号 == 'SN-SELF-001'

    def test_cross_branch_same_serial_allowed(self, manager_user, branch, second_branch):
        """同分公司口径（serial-dedup-scope）：手机自编编号跨分公司同号合法。"""
        from conftest import _client_for
        _grant(manager_user)
        item = _item('SN-UQ-6')
        _inst(branch, item, 1, serial='办公手机-3')
        b = _inst(second_branch, item, 2)
        resp = _client_for(manager_user).patch(
            f'/api/assets/fixed-assets/{b.id}/supplement',
            {'序列号': '办公手机-3'}, format='json')
        assert resp.status_code == status.HTTP_200_OK
        b.refresh_from_db()
        assert b.序列号 == '办公手机-3'


@pytest.mark.django_db
class TestReportCommand:
    def test_reports_duplicates_and_exits_nonzero(self, db):
        """0029 约束后同分公司重复不可构造；无分公司（branch=NULL）行不受唯一
        索引约束（NULL 互异）且属真实合法状态——以其验证命令的分组报告逻辑。"""
        from io import StringIO
        from django.core.management import call_command
        item = _item('SN-CMD-1')
        _inst(None, item, 1, serial='SN-DUP-X')
        _inst(None, item, 2, serial='SN-DUP-X')
        out = StringIO()
        with pytest.raises(SystemExit) as e:
            call_command('report_serial_duplicates', stdout=out)
        assert e.value.code == 1
        assert 'SN-DUP-X' in out.getvalue()
        assert '2 台' in out.getvalue()

    def test_clean_db_exits_zero(self, db):
        from io import StringIO
        from django.core.management import call_command
        out = StringIO()
        call_command('report_serial_duplicates', stdout=out)
        assert '无同分公司重复序列号' in out.getvalue()

    def test_cross_branch_same_serial_not_reported(self, branch, second_branch):
        """跨分公司同号合法，不计入重复（命令与约束同为分公司口径）。"""
        from io import StringIO
        from django.core.management import call_command
        item = _item('SN-CMD-2')
        _inst(branch, item, 1, serial='SN-X-OVERLAP')
        _inst(second_branch, item, 2, serial='SN-X-OVERLAP')
        out = StringIO()
        call_command('report_serial_duplicates', stdout=out)
        assert '无同分公司重复序列号' in out.getvalue()


@pytest.mark.django_db
class TestDbUniqueConstraint:
    """阶段二 DB 约束（unique_branch_serial）：应用层查重的最终兜底。"""

    def test_db_rejects_same_branch_duplicate(self, branch):
        item = _item('SN-DB-1')
        _inst(branch, item, 1, serial='SN-DB-X')
        with pytest.raises(Exception) as e:
            _inst(branch, item, 2, serial='SN-DB-X')
        assert 'unique' in str(e.value).lower()

    def test_cross_branch_and_empty_not_restricted(self, branch, second_branch):
        item = _item('SN-DB-2')
        _inst(branch, item, 1, serial='SN-DB-Y')
        _inst(second_branch, item, 2, serial='SN-DB-Y')  # 跨分公司同号合法
        _inst(branch, item, 3, serial='')
        _inst(branch, item, 4, serial='')  # 空=待补录，多台不受限
