"""Organization tests: branch code format validation, Region/Branch/Team CRUD."""
import pytest
from django.test import TransactionTestCase
from rest_framework import status


@pytest.mark.django_db
class TestBranchCodeValidation:
    def test_create_branch_valid_code(self, authenticated_client, team):
        resp = authenticated_client.post('/api/branches/', {
            'name': '上海分公司', 'code': 'SH001', 'team': team.id, 'status': 'active',
        })
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data['code'] == 'SH001'

    def test_create_branch_lowercase_auto_uppercase(self, authenticated_client, team):
        resp = authenticated_client.post('/api/branches/', {
            'name': '北京分公司', 'code': 'bj001', 'team': team.id, 'status': 'active',
        })
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data['code'] == 'BJ001'

    def test_create_branch_stripped_whitespace(self, authenticated_client, team):
        resp = authenticated_client.post('/api/branches/', {
            'name': '广州分公司', 'code': ' GZ001 ', 'team': team.id, 'status': 'active',
        })
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data['code'] == 'GZ001'

    def test_create_branch_invalid_format_chinese(self, authenticated_client, team):
        resp = authenticated_client.post('/api/branches/', {
            'name': '测试分公司', 'code': '上海001', 'team': team.id, 'status': 'active',
        })
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_branch_invalid_format_short_number(self, authenticated_client, team):
        resp = authenticated_client.post('/api/branches/', {
            'name': '测试分公司', 'code': 'SH01', 'team': team.id, 'status': 'active',
        })
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_branch_invalid_format_dash(self, authenticated_client, team):
        resp = authenticated_client.post('/api/branches/', {
            'name': '测试分公司', 'code': 'SH-001', 'team': team.id, 'status': 'active',
        })
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_branch_4_letter_prefix(self, authenticated_client, team):
        resp = authenticated_client.post('/api/branches/', {
            'name': '哈尔滨分公司', 'code': 'HRB001', 'team': team.id, 'status': 'active',
        })
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data['code'] == 'HRB001'

    def test_create_branch_duplicate_code_returns_400(self, authenticated_client, branch):
        # branch 已存在（code=CS001），再用同 code 创建 → 400（不再 500）
        resp = authenticated_client.post('/api/branches/', {
            'name': '重名分公司', 'code': branch.code, 'team': branch.team_id, 'status': 'active',
        })
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert '已存在' in resp.data['code'][0]

    def test_update_branch_keep_own_code(self, authenticated_client, branch):
        # 编辑分公司，code 保持自身 → 通过（排除自身，不误判重复）
        resp = authenticated_client.patch(f'/api/branches/{branch.id}', {
            'code': branch.code,
        })
        assert resp.status_code == status.HTTP_200_OK


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

    def test_delete_branch_no_assets(self, authenticated_client, team):
        # Create a fresh branch with no assets
        resp = authenticated_client.post('/api/branches/', {
            'name': '待删除分公司', 'code': 'DL001', 'team': team.id, 'status': 'active',
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

    def test_update_team_change_leader_no_member_writeback(
        self, authenticated_client, region, leader_user, staff_user,
    ):
        from apps.organizations.models import Team
        team = Team.objects.create(name='行政组A', region=region, leader=leader_user, status='active')

        resp = authenticated_client.patch(f'/api/teams/{team.id}', {
            'leader': staff_user.id,
        })
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['leader'] == staff_user.id

        # 组长指派只写树节点字段，不回写员工的组织归属（分公司保持原值）
        staff_user.refresh_from_db()
        assert staff_user.branch_id is not None  # fixture 挂靠分公司，未被清空/改动

    def test_delete_team_with_branches_rejected(self, authenticated_client, region, branch):
        from apps.organizations.models import Team
        team = branch.team
        resp = authenticated_client.delete(f'/api/teams/{team.id}')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert '分公司' in resp.data['detail']

    def test_delete_empty_team_ok(self, authenticated_client, region):
        from apps.organizations.models import Team
        team = Team.objects.create(name='待删除空组', region=region, status='active')
        resp = authenticated_client.delete(f'/api/teams/{team.id}')
        assert resp.status_code == status.HTTP_204_NO_CONTENT

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


@pytest.mark.django_db
class TestBranchTeam:
    """分公司隶属行政组（Branch.team 必填唯一父级）"""

    def test_create_branch_with_team(self, authenticated_client, region):
        from apps.organizations.models import Team
        team = Team.objects.create(name='行政组A', region=region, status='active')
        resp = authenticated_client.post('/api/branches/', {
            'name': '测试分公司', 'code': 'TS001',
            'team': team.id, 'status': 'active',
        })
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data['team'] == team.id
        assert resp.data['region'] == str(region.id)  # 派生只读字段 = team.region

    def test_create_branch_without_team_rejected(self, authenticated_client, region):
        resp = authenticated_client.post('/api/branches/', {
            'name': '无组分公司', 'code': 'TS003', 'status': 'active',
        })
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_branch_region_is_derived_not_writable(self, authenticated_client, region, branch, team):
        resp = authenticated_client.patch(f'/api/branches/{branch.id}', {'region': region.id})
        assert resp.status_code == status.HTTP_200_OK
        branch.refresh_from_db()
        assert branch.team_id == team.id  # region 写入被忽略，不产生实际变更


class TestBackfillMigration(TransactionTestCase):
    """organizations.0007：存量分公司 team 回填（员工众数 → 区域兜底组）"""

    def _migrate_back_and_seed(self, executor):
        """回退到 0006 状态（Branch.region 尚存、team 可空、User 有 team）并造数据。"""
        from django.contrib.auth.hashers import make_password

        executor.migrate([
            ('users', '0005_alter_user_role'),
            ('organizations', '0006_company'),
        ])
        old_state = executor.loader.project_state([
            ('users', '0005_alter_user_role'),
            ('organizations', '0006_company'),
        ])
        OldBranch = old_state.apps.get_model('organizations', 'Branch')
        OldTeam = old_state.apps.get_model('organizations', 'Team')
        OldRegion = old_state.apps.get_model('organizations', 'Region')
        OldUser = old_state.apps.get_model('users', 'User')

        region = OldRegion.objects.create(name='回填区域', code='BF001', status='active')
        team_a = OldTeam.objects.create(name='A组', region=region, status='active')
        team_b = OldTeam.objects.create(name='B组', region=region, status='active')

        # 分公司1：员工众数 → A组（3 A / 1 B）
        b1 = OldBranch.objects.create(name='众数分公司', code='BF101', region=region, status='active')
        for i, t in enumerate([team_a, team_a, team_a, team_b]):
            OldUser.objects.create(
                phone=f'1310000000{i}', name=f'员工{i}', role='staff',
                status='active', password=make_password('x'), branch=b1, team=t,
            )
        # 分公司2：无员工 → 兜底组
        OldBranch.objects.create(name='无信号分公司', code='BF102', region=region, status='active')

        return region, team_a

    def test_backfill_mode_and_fallback(self):
        from django.db import connection
        from django.db.migrations.executor import MigrationExecutor
        from apps.organizations.models import Branch, Team

        executor = MigrationExecutor(connection)
        region, team_a = self._migrate_back_and_seed(executor)
        try:
            # loader 会缓存 applied 状态，正向迁移用新 executor 才能识别真实状态
            forward_executor = MigrationExecutor(connection)
            forward_executor.migrate([('organizations', '0007_branch_team_single_parent')])

            b1 = Branch.objects.get(code='BF101')
            assert b1.team_id == team_a.id  # 员工众数回填

            b2 = Branch.objects.get(code='BF102')
            fallback = Team.objects.get(name=f'{region.name}未分组')
            assert b2.team_id == fallback.id  # 区域兜底组
            assert Branch.objects.filter(team__isnull=True).count() == 0  # 约束生效，无遗漏
        finally:
            restore_executor = MigrationExecutor(connection)
            restore_executor.migrate(restore_executor.loader.graph.leaf_nodes())  # 恢复到最新迁移状态


@pytest.mark.django_db
class TestCompany:
    """集团（Company 单例）：读、管理员改名、非管理员禁止"""

    def test_get_company_returns_name(self, authenticated_client):
        resp = authenticated_client.get('/api/company/')
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['name'] == '启航集团'

    def test_admin_update_company_name(self, authenticated_client):
        resp = authenticated_client.patch('/api/company/', {'name': '新集团名'})
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['name'] == '新集团名'
        resp2 = authenticated_client.get('/api/company/')
        assert resp2.data['name'] == '新集团名'

    def test_staff_cannot_update_company(self, staff_client):
        resp = staff_client.patch('/api/company/', {'name': '违规改名'})
        assert resp.status_code == status.HTTP_403_FORBIDDEN
