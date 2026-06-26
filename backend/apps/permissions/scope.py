from dataclasses import dataclass, field


@dataclass
class Scope:
    """解析后的用户管理数据范围。"""

    all: bool = False
    regions: set = field(default_factory=set)
    branches: set = field(default_factory=set)
    teams: set = field(default_factory=set)

    @property
    def is_empty(self) -> bool:
        return not (self.regions or self.branches or self.teams)


def resolve_user_scope(user) -> Scope:
    """解析用户的管理数据范围。

    admin 返回全部；否则取其组织节点授权并集，并将 region 展开为旗下分公司。
    结果缓存在用户实例上（_mgmt_scope_cache），单次请求内不重复计算。
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

    # region 授权展开为旗下全部分公司
    if regions:
        from apps.organizations.models import Branch
        branches.update(
            Branch.objects.filter(region_id__in=regions).values_list('id', flat=True)
        )

    scope = Scope(all=False, regions=regions, branches=branches, teams=teams)
    user._mgmt_scope_cache = scope
    return scope
