from dataclasses import dataclass, field


@dataclass
class Scope:
    """解析后的账号数据范围。管理员全量；自定义节点覆盖默认归属。"""

    all: bool = False
    regions: set = field(default_factory=set)
    branches: set = field(default_factory=set)
    teams: set = field(default_factory=set)

    @property
    def is_empty(self) -> bool:
        return not (self.all or self.regions or self.branches or self.teams)


def resolve_user_scope(user) -> Scope:
    """计算账号数据范围：系统管理员全量；否则显式节点覆盖归属默认值。"""
    if user is None or not getattr(user, 'is_authenticated', False):
        return Scope()

    cached = getattr(user, '_mgmt_scope_cache', None)
    if cached is not None:
        return cached

    if getattr(user, 'role', None) == 'admin':
        scope = Scope(all=True)
        user._mgmt_scope_cache = scope
        return scope

    explicit_scopes = list(user.management_scopes.all())
    if explicit_scopes:
        if any(s.is_all_data for s in explicit_scopes):
            scope = Scope(all=True)
        else:
            regions = {s.region_id for s in explicit_scopes if s.region_id}
            teams = {s.team_id for s in explicit_scopes if s.team_id}
            branches = {s.branch_id for s in explicit_scopes if s.branch_id}
            if regions or teams:
                from apps.organizations.models import Branch
                if regions:
                    branches.update(
                        Branch.objects.filter(team__region_id__in=regions)
                        .values_list('id', flat=True)
                    )
                if teams:
                    branches.update(
                        Branch.objects.filter(team_id__in=teams).values_list('id', flat=True)
                    )
            scope = Scope(regions=regions, branches=branches, teams=teams)
    else:
        # An account without an override receives its assigned branch scope,
        # or falls back to the team's branches if only a team is assigned.
        branch_id = getattr(user, 'branch_id', None)
        team_id = getattr(user, 'team_id', None)
        if branch_id:
            scope = Scope(branches={branch_id})
        elif team_id:
            from apps.organizations.models import Branch
            team_branches = set(
                Branch.objects.filter(team_id=team_id).values_list('id', flat=True)
            )
            scope = Scope(branches=team_branches, teams={team_id})
        else:
            scope = Scope()

    user._mgmt_scope_cache = scope
    return scope
