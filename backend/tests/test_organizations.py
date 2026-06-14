"""Organization tests: branch code format validation, Region/Branch/Team CRUD."""
import pytest
from rest_framework import status


@pytest.mark.django_db
class TestBranchCodeValidation:
    def test_create_branch_valid_code(self, authenticated_client, region):
        resp = authenticated_client.post('/api/branches/', {
            'name': '上海分公司', 'code': 'SH001', 'region': region.id, 'status': 'active',
        })
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data['code'] == 'SH001'

    def test_create_branch_lowercase_auto_uppercase(self, authenticated_client, region):
        resp = authenticated_client.post('/api/branches/', {
            'name': '北京分公司', 'code': 'bj001', 'region': region.id, 'status': 'active',
        })
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data['code'] == 'BJ001'

    def test_create_branch_stripped_whitespace(self, authenticated_client, region):
        resp = authenticated_client.post('/api/branches/', {
            'name': '广州分公司', 'code': ' GZ001 ', 'region': region.id, 'status': 'active',
        })
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data['code'] == 'GZ001'

    def test_create_branch_invalid_format_chinese(self, authenticated_client, region):
        resp = authenticated_client.post('/api/branches/', {
            'name': '测试分公司', 'code': '上海001', 'region': region.id, 'status': 'active',
        })
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_branch_invalid_format_short_number(self, authenticated_client, region):
        resp = authenticated_client.post('/api/branches/', {
            'name': '测试分公司', 'code': 'SH01', 'region': region.id, 'status': 'active',
        })
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_branch_invalid_format_dash(self, authenticated_client, region):
        resp = authenticated_client.post('/api/branches/', {
            'name': '测试分公司', 'code': 'SH-001', 'region': region.id, 'status': 'active',
        })
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_branch_4_letter_prefix(self, authenticated_client, region):
        resp = authenticated_client.post('/api/branches/', {
            'name': '哈尔滨分公司', 'code': 'HRB001', 'region': region.id, 'status': 'active',
        })
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data['code'] == 'HRB001'


# ---------------------------------------------------------------------------
# Region CRUD
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestRegionCRUD:
    def test_admin_create_region(self, authenticated_client):
        resp = authenticated_client.post('/api/regions/', {
            'name': '华东区域', 'code': 'HD', 'status': 'active',
        })
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data['name'] == '华东区域'
        assert resp.data['code'] == 'HD'

    def test_create_region_duplicate_code(self, authenticated_client, region):
        resp = authenticated_client.post('/api/regions/', {
            'name': '另一个区域', 'code': region.code, 'status': 'active',
        })
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_list_regions(self, authenticated_client, region, second_region):
        resp = authenticated_client.get('/api/regions/')
        assert resp.status_code == status.HTTP_200_OK
        ids = [r['id'] for r in resp.data]
        assert str(region.id) in ids
        assert str(second_region.id) in ids

    def test_list_regions_no_pagination(self, authenticated_client, region):
        resp = authenticated_client.get('/api/regions/')
        assert resp.status_code == status.HTTP_200_OK
        # pagination_class=None means the response is a plain list, not paginated
        assert isinstance(resp.data, list)

    def test_update_region_name(self, authenticated_client, region):
        resp = authenticated_client.patch(f'/api/regions/{region.id}', {
            'name': '更新后区域名',
        })
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['name'] == '更新后区域名'

    def test_delete_region_no_branches(self, authenticated_client, region):
        # Create a fresh region with no branches
        resp = authenticated_client.post('/api/regions/', {
            'name': '待删除区域', 'code': 'DEL', 'status': 'active',
        })
        region_id = resp.data['id']
        del_resp = authenticated_client.delete(f'/api/regions/{region_id}')
        assert del_resp.status_code == status.HTTP_204_NO_CONTENT

    def test_delete_region_with_protected_branches(
        self, authenticated_client, region, branch, make_asset,
    ):
        # Branch has a protected asset, so cascading delete of branch fails
        make_asset(branch=branch)
        resp = authenticated_client.delete(f'/api/regions/{region.id}')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


# ---------------------------------------------------------------------------
# Branch CRUD (expanded)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestBranchCRUD:
    def test_update_branch_name(self, authenticated_client, branch, region):
        resp = authenticated_client.patch(f'/api/branches/{branch.id}', {
            'name': '新分公司名',
        })
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['name'] == '新分公司名'

    def test_delete_branch_no_assets(self, authenticated_client, region):
        # Create a fresh branch with no assets
        resp = authenticated_client.post('/api/branches/', {
            'name': '待删除分公司', 'code': 'DL001', 'region': region.id, 'status': 'active',
        })
        branch_id = resp.data['id']
        del_resp = authenticated_client.delete(f'/api/branches/{branch_id}')
        assert del_resp.status_code == status.HTTP_204_NO_CONTENT

    def test_delete_branch_with_assets(self, authenticated_client, branch, make_asset):
        make_asset(branch=branch)
        resp = authenticated_client.delete(f'/api/branches/{branch.id}')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert '资产' in resp.data['detail']

    def test_list_branches_no_pagination(self, authenticated_client, branch):
        resp = authenticated_client.get('/api/branches/')
        assert resp.status_code == status.HTTP_200_OK
        assert isinstance(resp.data, list)

    def test_filter_branches_by_region(
        self, authenticated_client, region, second_region, branch, second_branch,
    ):
        resp = authenticated_client.get(f'/api/branches/?region={region.id}')
        assert resp.status_code == status.HTTP_200_OK
        ids = [b['id'] for b in resp.data]
        assert str(branch.id) in ids
        assert str(second_branch.id) not in ids


# ---------------------------------------------------------------------------
# Team CRUD
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestTeamCRUD:
    def test_create_team_with_region(self, authenticated_client, region):
        resp = authenticated_client.post('/api/teams/', {
            'name': '测试行政组', 'region': region.id, 'status': 'active',
        })
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data['name'] == '测试行政组'
        assert resp.data['region'] == region.id

    def test_update_team_change_leader(
        self, authenticated_client, region, leader_user, staff_user,
    ):
        from apps.organizations.models import Team
        team = Team.objects.create(name='行政组A', region=region, leader=leader_user, status='active')
        # Simulate what perform_create does: auto-assign leader to this team
        leader_user.team = team
        leader_user.save(update_fields=['team', 'updated_at'])

        resp = authenticated_client.patch(f'/api/teams/{team.id}', {
            'leader': staff_user.id,
        })
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['leader'] == staff_user.id

        # New leader should be auto-assigned to this team
        staff_user.refresh_from_db()
        assert staff_user.team_id == team.id

    def test_delete_team_clears_members(self, authenticated_client, region, staff_user):
        from apps.organizations.models import Team
        team = Team.objects.create(name='待删除组', region=region, status='active')
        staff_user.team = team
        staff_user.save(update_fields=['team', 'updated_at'])

        resp = authenticated_client.delete(f'/api/teams/{team.id}')
        assert resp.status_code == status.HTTP_204_NO_CONTENT

        staff_user.refresh_from_db()
        assert staff_user.team_id is None

    def test_filter_teams_by_region(self, authenticated_client, region, second_region):
        from apps.organizations.models import Team
        Team.objects.create(name='区域A组', region=region, status='active')
        Team.objects.create(name='区域B组', region=second_region, status='active')

        resp = authenticated_client.get(f'/api/teams/?region={region.id}')
        assert resp.status_code == status.HTTP_200_OK
        names = [t['name'] for t in resp.data]
        assert '区域A组' in names
        assert '区域B组' not in names

    def test_staff_cannot_create_team(self, staff_client, region):
        resp = staff_client.post('/api/teams/', {
            'name': '非法创建', 'region': region.id, 'status': 'active',
        })
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_admin_can_create_team(self, authenticated_client, region):
        resp = authenticated_client.post('/api/teams/', {
            'name': '组合法创建', 'region': region.id, 'status': 'active',
        })
        assert resp.status_code == status.HTTP_201_CREATED
