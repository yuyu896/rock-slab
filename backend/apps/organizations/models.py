from django.db import models
from django.core.validators import RegexValidator
from core.models import UUIDModel, TimestampedModel

BRANCH_CODE_REGEX = r'^[A-Z]{2,4}[0-9]{3}$'


class Region(UUIDModel, TimestampedModel):
    """区域"""
    name = models.CharField('区域名称', max_length=100)
    code = models.CharField('区域编码', max_length=50, unique=True)
    manager = models.ForeignKey(
        'users.User', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='managed_regions',
        verbose_name='区域负责人',
    )
    status = models.CharField(
        '状态', max_length=10,
        choices=[('active', 'active'), ('inactive', 'inactive')],
        default='active',
    )

    class Meta:
        db_table = 'organizations_region'
        ordering = ['code']
        verbose_name = '区域'
        verbose_name_plural = '区域'

    def __str__(self):
        return self.name


class Branch(UUIDModel, TimestampedModel):
    """分公司"""
    name = models.CharField('分公司名称', max_length=100)
    code = models.CharField(
        '分公司编码', max_length=50, unique=True,
        validators=[RegexValidator(
            regex=BRANCH_CODE_REGEX,
            message='编号格式为2-4位大写字母(城市缩写)+3位数字，如 SH001',
        )],
    )
    team = models.ForeignKey(
        'organizations.Team', on_delete=models.PROTECT,
        related_name='branches', verbose_name='所属行政组',
    )
    address = models.CharField('地址', max_length=255, blank=True, default='')
    manager = models.ForeignKey(
        'users.User', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='managed_branches',
        verbose_name='分公司负责人',
    )
    phone = models.CharField('联系电话', max_length=20, blank=True, default='')
    status = models.CharField(
        '状态', max_length=10,
        choices=[('active', 'active'), ('inactive', 'inactive')],
        default='active',
    )

    class Meta:
        db_table = 'organizations_branch'
        ordering = ['code']
        verbose_name = '分公司'
        verbose_name_plural = '分公司'

    def __str__(self):
        return self.name


class Team(UUIDModel, TimestampedModel):
    """行政组"""
    name = models.CharField('组名', max_length=100)
    region = models.ForeignKey(
        Region, on_delete=models.CASCADE,
        related_name='teams', verbose_name='所属区域',
    )
    leader = models.ForeignKey(
        'users.User', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='led_teams',
        verbose_name='组长',
    )
    status = models.CharField(
        '状态', max_length=10,
        choices=[('active', 'active'), ('inactive', 'inactive')],
        default='active',
    )

    class Meta:
        db_table = 'organizations_team'
        ordering = ['name']
        verbose_name = '行政组'
        verbose_name_plural = '行政组'

    def __str__(self):
        return self.name


class Company(UUIDModel, TimestampedModel):
    """集团（系统单例，顶层组织名）"""
    name = models.CharField('集团名称', max_length=100, default='启航集团')

    class Meta:
        db_table = 'organizations_company'
        verbose_name = '集团'
        verbose_name_plural = '集团'

    def __str__(self):
        return self.name

    @classmethod
    def get_singleton(cls):
        obj = cls.objects.first()
        return obj if obj else cls.objects.create(name='启航集团')


class Department(UUIDModel, TimestampedModel):
    """部门字典 —— 归属标签（分公司 × 部门名），不是组织树节点。

    不参与组织树层级与数据范围推导；用于资产/单据表单的部门下拉归一（P1 允许
    字典外自由输入，P2 随领用单绑部门 FK 化时收紧）。
    """

    branch = models.ForeignKey(
        Branch, on_delete=models.CASCADE,
        related_name='departments', verbose_name='所属分公司',
    )
    name = models.CharField('部门名称', max_length=100)

    class Meta:
        db_table = 'organizations_department'
        ordering = ['branch__name', 'name']
        verbose_name = '部门'
        verbose_name_plural = '部门字典'
        constraints = [
            models.UniqueConstraint(fields=['branch', 'name'], name='uniq_department_branch_name'),
        ]

    def __str__(self):
        return f'{self.branch.name}·{self.name}'
