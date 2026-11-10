"""Tests for user.team field and associated scope/validation behavior."""
import pytest
from rest_framework import status
from conftest import _client_for


def _grant(user, *codes):
    from apps.permissions.models import OperationGrant
    OperationGrant.objects.bulk_create(
        [OperationGrant(user=user, code=code) for code in codes],
        ignore_conflicts=True,
    )


# ---------------------------------------------------------------------------
# 6.1  创建 branch=null, team=<id> 的员工 — team 保存，branch 为 null
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_create_user_with_team_only(admin_user, team):
    from apps.users.models import User

    user = User.objects.create_user(
        phone='13877770001', name='行政组员工', password='test123456',
        role='leader', status='active', team=team,
    )
    user.refresh_from_db()
    assert user.team_id == team.id
    assert user.branch_id is None


# ---------------------------------------------------------------------------
# 6.2  创建 branch + team 同时传入 — team 被互斥清空
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_create_user_branch_clears_team_via_api(authenticated_client, branch, team):
    """API 路径：branch 有值时 validate() 把 team 强制为 null。"""
    payload = {
        'phone': '13877770002', 'name': '双填员工', 'role': 'leader',
        'status': 'active', 'password': 'test123456',
        'branch': str(branch.id), 'team': str(team.id),
    }
    resp = authenticated_client.post('/api/users/', payload, format='json')
    assert resp.status_code == status.HTTP_201_CREATED
    from apps.users.models import User
    created = User.objects.get(phone='13877770002')
    assert created.branch_id == branch.id
    assert created.team_id is None


# ---------------------------------------------------------------------------
# 6.3  仅归属行政组员工的 resolve_user_scope 含该 team 下分公司
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_resolve_scope_team_only_includes_team_branches(team, branch):
    """无显式 ManagementScope、branch=null、team 有值 → scope.branches 含 team 下分公司。"""
    from apps.users.models import User
    from apps.permissions.scope import resolve_user_scope

    team_user = User.objects.create_user(
        phone='13877770003', name='行政组负责人', password='test123456',
        role='leader', status='active', team=team,
    )
    scope = resolve_user_scope(team_user)
    assert branch.id in scope.branches
    assert team.id in scope.teams
    assert not scope.all


# ---------------------------------------------------------------------------
# 6.4  _validate_in_scope：team 直属员工在操作者范围内时通过，范围外时拒绝
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_validate_in_scope_allows_team_member(admin_user, team, branch, second_branch, second_team):
    """manager 有 team scope → 其下 branch 员工可见；另行政组员工也可管理。"""
    from apps.users.models import User
    from apps.permissions.models import ManagementScope, OperationGrant
    from apps.users.views import UserViewSet
    from rest_framework.serializers import ValidationError

    # operator：有 team 的显式 ManagementScope
    operator = User.objects.create_user(
        phone='13877770004', name='行政组管理员', password='test123456',
        role='manager', status='active',
    )
    ManagementScope.objects.create(user=operator, team=team)
    OperationGrant.objects.bulk_create([
        OperationGrant(user=operator, code=c) for c in ('view_users', 'edit_users')
    ], ignore_conflicts=True)

    # target_in_team: branch=null, team=team（直属行政组）
    target_in = User.objects.create_user(
        phone='13877770005', name='范围内行政组员工', password='test123456',
        role='leader', status='active', team=team,
    )
    # _validate_in_scope 不应抛出
    view = UserViewSet()
    view._validate_in_scope(operator, target_in)

    # target_out_of_scope: 属于 second_team（不在 operator 范围）
    target_out = User.objects.create_user(
        phone='13877770006', name='范围外员工', password='test123456',
        role='leader', status='active', team=second_team,
    )
    with pytest.raises(ValidationError):
        view._validate_in_scope(operator, target_out)
