"""
Tests for asset CRUD permissions (add-asset-crud-permissions).
"""
import pytest
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.fixture
def region_a(db):
    from apps.organizations.models import Region
    return Region.objects.create(name='大区A', code='TSTA', status='active')


@pytest.fixture
def region_b(db):
    from apps.organizations.models import Region
    return Region.objects.create(name='大区B', code='TSTB', status='active')


@pytest.fixture
def branch_a(db, region_a):
    from apps.organizations.models import Branch
    return Branch.objects.create(name='分公司A', code='TSA01', region=region_a, status='active')


@pytest.fixture
def branch_b(db, region_b):
    from apps.organizations.models import Branch
    return Branch.objects.create(name='分公司B', code='TSB01', region=region_b, status='active')


@pytest.fixture
def supervisor_a(db, region_a, branch_a):
    return User.objects.create_user(
        phone='13900010001', name='主管A', password='test123456',
        role='supervisor', status='active', region=region_a, branch=branch_a,
    )


@pytest.fixture
def leader_a(db, branch_a):
    return User.objects.create_user(
        phone='13900020001', name='组长A', password='test123456',
        role='leader', status='active', branch=branch_a,
    )


@pytest.fixture
def staff_a(db, branch_a):
    return User.objects.create_user(
        phone='13900030001', name='专员A', password='test123456',
        role='staff', status='active', branch=branch_a,
    )


def _client(user):
    from apps.authentication.models import ExpiringToken
    client = APIClient()
    token, _ = ExpiringToken.objects.get_or_create(user=user)
    client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
    return client


@pytest.fixture
def asset_a(db, branch_a):
    from apps.assets.models import Asset
    return Asset.objects.create(
        序号=1, 分公司='分公司A', 分公司编号='TSA01', 资产编号='CRUD-001',
        资产类目='固定', 物品分类='办公', 资产名称='测试资产', 数量=1,
        branch=branch_a,
    )


@pytest.fixture
def asset_b(db, branch_b):
    from apps.assets.models import Asset
    return Asset.objects.create(
        序号=2, 分公司='分公司B', 分公司编号='TSB01', 资产编号='CRUD-002',
        资产类目='固定', 物品分类='办公', 资产名称='其他区域资产', 数量=1,
        branch=branch_b,
    )


@pytest.mark.django_db
class TestAssetUpdatePermissions:
    def test_supervisor_update_own_region(self, supervisor_a, asset_a):
        client = _client(supervisor_a)
        resp = client.patch(f'/api/assets/{asset_a.id}', {'资产名称': '已修改'})
        assert resp.status_code == 200
        asset_a.refresh_from_db()
        assert asset_a.资产名称 == '已修改'

    def test_supervisor_update_other_region_404(self, supervisor_a, asset_b):
        client = _client(supervisor_a)
        resp = client.patch(f'/api/assets/{asset_b.id}', {'资产名称': '尝试修改'})
        assert resp.status_code == 404

    def test_leader_update_forbidden(self, leader_a, asset_a):
        client = _client(leader_a)
        resp = client.patch(f'/api/assets/{asset_a.id}', {'资产名称': '尝试修改'})
        assert resp.status_code == 403


@pytest.mark.django_db
class TestAssetDeletePermissions:
    def test_supervisor_delete_own_region(self, supervisor_a, asset_a):
        from apps.assets.models import Asset
        client = _client(supervisor_a)
        resp = client.delete(f'/api/assets/{asset_a.id}')
        assert resp.status_code == 204
        assert not Asset.objects.filter(id=asset_a.id).exists()

    def test_staff_delete_forbidden(self, staff_a, asset_a):
        client = _client(staff_a)
        resp = client.delete(f'/api/assets/{asset_a.id}')
        assert resp.status_code == 403


@pytest.mark.django_db
class TestAssetBranchSync:
    def test_branch_change_syncs_denormalized_fields(self, supervisor_a, asset_a, branch_b):
        client = _client(supervisor_a)
        # supervisor_a is in region_a, can only update assets in own region
        # So we need admin to do cross-region update, or test with same region
        from apps.organizations.models import Branch
        branch_a2 = Branch.objects.create(
            name='分公司A2', code='TSA02', region=supervisor_a.region, status='active',
        )
        resp = client.patch(f'/api/assets/{asset_a.id}', {'branch': branch_a2.id})
        assert resp.status_code == 200
        asset_a.refresh_from_db()
        assert asset_a.分公司 == '分公司A2'
        assert asset_a.分公司编号 == 'TSA02'
