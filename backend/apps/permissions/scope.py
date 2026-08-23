from dataclasses import dataclass, field


@dataclass
class Scope:
    """解析后的用户管理数据范围。

    范围来源 = 组织节点授权（ManagementScope）∪ 树负责人任命：
    appointed_* 为任命来源集合（仅展示用），branches 为全部来源沿树展开的并集。
    """

    all: bool = False
    regions: set = field(default_factory=set)
    branches: set = field(default_factory=set)
    teams: set = field(default_factory=set)
    appointed_regions: set = field(default_factory=set)
    appointed_teams: set = field(default_factory=set)
    appointed_branches: set = field(default_factory=set)

    @property
    def is_empty(self) -> bool:
        return not (self.regions or self.branches or self.teams
                    or self.appointed_regions or self.appointed_teams or self.appointed_branches)


def resolve_user_scope(user) -> Scope:
    """解析用户的管理数据范围。

    admin 返回全部；否则取「组织节点授权 ∪ 树负责人任命」并集，沿组织树展开为
    分公司集合（region → 旗下行政组 → 分公司；team → 组内分公司）。
    任命即授权：Region.manager / Team.leader / Branch.manager 的子树范围实时并入，
    无需任何授权记录。结果缓存在用户实例上（_mgmt_scope_cache），单次请求内不重复计算。
    """
    if user is None or not getattr(user, 'is_authenticated', False):
        return Scope()

    cached = getattr(user, '_mgmt_scope_cache', None)
    if cached is not None:
        return cached

    if getattr(user, 'role', None) == 'admin':
        scope = Scope(all=True)
        user._mgmt_scope_cache = scope
        return scope

    # 「全部数据」授权：单条即等价全部组织数据（含未来新增节点）
    if user.management_scopes.filter(is_all_data=True).exists():
        scope = Scope(all=True)
        user._mgmt_scope_cache = scope
        return scope

    regions, branches, teams = set(), set(), set()
    for s in user.management_scopes.all():
        if s.region_id:
            regions.add(s.region_id)
        elif s.branch_id:
            branches.add(s.branch_id)
        elif s.team_id:
            teams.add(s.team_id)

    # 任命即授权：树负责人 = 子树范围
    from apps.organizations.models import Region, Team, Branch
    appointed_regions = set(
        Region.objects.filter(manager=user).values_list('id', flat=True)
    )
    appointed_teams = set(
        Team.objects.filter(leader=user).values_list('id', flat=True)
    )
    appointed_branches = set(
        Branch.objects.filter(manager=user).values_list('id', flat=True)
    )

    all_regions = regions | appointed_regions
    all_teams = teams | appointed_teams
    branches |= appointed_branches

    # 树遍历展开：region → 旗下行政组 → 分公司；team → 组内分公司
    if all_regions or all_teams:
        if all_regions:
            branches.update(
                Branch.objects.filter(team__region_id__in=all_regions).values_list('id', flat=True)
            )
        if all_teams:
            branches.update(
                Branch.objects.filter(team_id__in=all_teams).values_list('id', flat=True)
            )

    scope = Scope(
        all=False,
        regions=all_regions,
        branches=branches,
        teams=all_teams,
        appointed_regions=appointed_regions,
        appointed_teams=appointed_teams,
        appointed_branches=appointed_branches,
    )
    user._mgmt_scope_cache = scope
    return scope
