from django.core.exceptions import ValidationError
from django.db import models
from core.models import UUIDModel, TimestampedModel
from .operations import OPERATION_CHOICES


class ManagementScope(UUIDModel, TimestampedModel):
    """管理授权（组织节点维度）——授予某用户管理一个大区 / 分公司 / 行政组 / 全部数据。

    is_all_data=True 表示「整个组织架构（全部数据）」授权，覆盖全部组织（含未来新增节点），
    与具体节点互斥；此时 region/branch/team 均为空。
    否则 region / branch / team 至多填一个，代表授权粒度：
      - region：管理该大区（含旗下全部分公司 / 行政组）
      - branch：管理该分公司
      - team：管理该行政组
    一个用户可持有多条授权，范围取并集；is_all_data 至多一条。
    """

    user = models.ForeignKey(
        'users.User', on_delete=models.CASCADE,
        related_name='management_scopes', verbose_name='被授权员工',
    )
    is_all_data = models.BooleanField(
        '全部数据', default=False,
        help_text='勾选后授权整个组织架构全部数据（含未来新增节点），与具体节点互斥',
    )
    region = models.ForeignKey(
        'organizations.Region', on_delete=models.CASCADE,
        null=True, blank=True, related_name='scoped_users',
        verbose_name='授权大区',
    )
    branch = models.ForeignKey(
        'organizations.Branch', on_delete=models.CASCADE,
        null=True, blank=True, related_name='scoped_users',
        verbose_name='授权分公司',
    )
    team = models.ForeignKey(
        'organizations.Team', on_delete=models.CASCADE,
        null=True, blank=True, related_name='scoped_users',
        verbose_name='授权行政组',
    )

    class Meta:
        db_table = 'permissions_management_scope'
        verbose_name = '管理授权（组织节点）'
        verbose_name_plural = '管理授权（组织节点）'
        ordering = ['-created_at']
        constraints = [
            # 「全部数据」或「恰好一个组织节点」二选一
            models.CheckConstraint(
                condition=(
                    models.Q(is_all_data=True, region__isnull=True, branch__isnull=True, team__isnull=True)
                    | (
                        models.Q(is_all_data=False)
                        & (
                            models.Q(region__isnull=True, branch__isnull=True, team__isnull=False)
                            | models.Q(region__isnull=True, branch__isnull=False, team__isnull=True)
                            | models.Q(region__isnull=False, branch__isnull=True, team__isnull=True)
                        )
                    )
                ),
                name='all_data_or_exactly_one_org_node',
            ),
            # 每用户至多一条「全部数据」授权
            models.UniqueConstraint(
                fields=['user'],
                condition=models.Q(is_all_data=True),
                name='uniq_user_all_data',
            ),
            # 去重：同一员工对同一节点只授权一次
            models.UniqueConstraint(
                fields=['user', 'region'],
                condition=models.Q(region__isnull=False),
                name='uniq_user_region',
            ),
            models.UniqueConstraint(
                fields=['user', 'branch'],
                condition=models.Q(branch__isnull=False),
                name='uniq_user_branch',
            ),
            models.UniqueConstraint(
                fields=['user', 'team'],
                condition=models.Q(team__isnull=False),
                name='uniq_user_team',
            ),
        ]

    def __str__(self):
        if self.is_all_data:
            return f'{self.user} → 全部数据'
        node = self.region or self.branch or self.team
        return f'{self.user} → {node}'

    def clean(self):
        nodes = [n for n in (self.region, self.branch, self.team) if n is not None]
        if self.is_all_data:
            if nodes:
                raise ValidationError('「全部数据」授权与具体组织节点互斥，请清除大区 / 分公司 / 行政组')
        else:
            if len(nodes) == 0:
                raise ValidationError('必须指定一个组织节点（大区 / 分公司 / 行政组），或勾选「全部数据」')
            if len(nodes) > 1:
                raise ValidationError('至多指定一个组织节点（大区 / 分公司 / 行政组 三选一）')


class OperationGrant(UUIDModel, TimestampedModel):
    """管理授权（业务操作维度）——授予某用户某项业务操作权限。"""

    user = models.ForeignKey(
        'users.User', on_delete=models.CASCADE,
        related_name='operation_grants', verbose_name='被授权员工',
    )
    code = models.CharField('业务操作', max_length=50, choices=OPERATION_CHOICES)

    class Meta:
        db_table = 'permissions_operation_grant'
        verbose_name = '管理授权（业务操作）'
        verbose_name_plural = '管理授权（业务操作）'
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(fields=['user', 'code'], name='uniq_user_operation'),
        ]

    def __str__(self):
        return f'{self.user} → {self.code}'
