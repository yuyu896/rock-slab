from rest_framework import serializers
from django.core.validators import RegexValidator
from apps.permissions.scope import resolve_user_scope
from .models import Region, Branch, Team, Company, BRANCH_CODE_REGEX, Department


def _assert_appointment_admin_only(serializer, attrs, field):
    """Only admins can change appointments; an appointment grants no permission or scope.

    Unchanged values and ordinary node edits that omit this field are allowed.
    """
    request = serializer.context.get('request')
    user = getattr(request, 'user', None)
    if user is None or not getattr(user, 'is_authenticated', False) or user.role == 'admin':
        return
    if field not in attrs:
        return
    current = getattr(serializer.instance, field, None) if serializer.instance else None
    if attrs[field] != current:
            raise serializers.ValidationError({field: ['只有系统管理员可以调整负责人任命']})


def _can_manage_region(context, region):
    request = context.get('request')
    user = getattr(request, 'user', None)
    if user is None or not getattr(user, 'is_authenticated', False):
        return False
    scope = resolve_user_scope(user)
    return scope.all or region.id in scope.regions


def _can_manage_team(context, team):
    request = context.get('request')
    user = getattr(request, 'user', None)
    if user is None or not getattr(user, 'is_authenticated', False):
        return False
    scope = resolve_user_scope(user)
    return scope.all or team.id in scope.teams or team.region_id in scope.regions


class RegionSerializer(serializers.ModelSerializer):
    can_manage = serializers.SerializerMethodField()

    class Meta:
        model = Region
        fields = [
            'id', 'name', 'code', 'manager', 'status', 'can_manage',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']

    def get_can_manage(self, obj):
        return _can_manage_region(self.context, obj)

    def validate(self, attrs):
        _assert_appointment_admin_only(self, attrs, 'manager')
        return attrs


class RegionWriteOptionSerializer(serializers.ModelSerializer):
    can_manage = serializers.SerializerMethodField()

    class Meta:
        model = Region
        fields = ['id', 'name', 'code', 'status', 'can_manage']

    def get_can_manage(self, obj):
        return _can_manage_region(self.context, obj)


class BranchSerializer(serializers.ModelSerializer):
    region = serializers.UUIDField(source='team.region_id', read_only=True)

    class Meta:
        model = Branch
        fields = [
            'id', 'name', 'code', 'team', 'region', 'address',
            'manager', 'phone', 'status',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at', 'region']
        extra_kwargs = {
            'code': {'validators': []},
        }

    def validate_code(self, value):
        value = value.strip().upper()
        validator = RegexValidator(
            regex=BRANCH_CODE_REGEX,
            message='编号格式为2-4位大写字母(城市缩写)+3位数字，如 SH001',
        )
        validator(value)
        qs = Branch.objects.filter(code=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(f'分公司编码 {value} 已存在')
        return value

    def validate(self, attrs):
        _assert_appointment_admin_only(self, attrs, 'manager')
        return attrs


class BranchOptionSerializer(serializers.ModelSerializer):
    """Minimal branch data for operation-scoped form selectors."""

    class Meta:
        model = Branch
        fields = ['id', 'name']


class BranchTreeOptionSerializer(serializers.ModelSerializer):
    team_name = serializers.CharField(source='team.name', read_only=True, allow_null=True)
    region = serializers.UUIDField(source='team.region_id', read_only=True, allow_null=True)
    region_name = serializers.CharField(source='team.region.name', read_only=True, allow_null=True)

    class Meta:
        model = Branch
        fields = ['id', 'name', 'team', 'team_name', 'region', 'region_name']


class BranchEditOptionSerializer(BranchTreeOptionSerializer):
    class Meta(BranchTreeOptionSerializer.Meta):
        fields = [
            'id', 'name', 'code', 'team', 'team_name', 'region', 'region_name',
            'address', 'phone', 'status',
        ]


class TeamSerializer(serializers.ModelSerializer):
    can_manage = serializers.SerializerMethodField()
    region_name = serializers.CharField(source='region.name', read_only=True)
    leader_name = serializers.CharField(source='leader.name', read_only=True, default=None)
    member_count = serializers.SerializerMethodField()

    class Meta:
        model = Team
        fields = [
            'id', 'name', 'region', 'region_name',
            'leader', 'leader_name', 'member_count',
            'status', 'can_manage', 'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']

    def get_can_manage(self, obj):
        return _can_manage_team(self.context, obj)

    def get_member_count(self, obj):
        from apps.users.models import User
        return User.objects.filter(branch__team=obj).count()

    def validate(self, attrs):
        _assert_appointment_admin_only(self, attrs, 'leader')
        return attrs


class TeamWriteOptionSerializer(serializers.ModelSerializer):
    can_manage = serializers.SerializerMethodField()

    class Meta:
        model = Team
        fields = ['id', 'name', 'region', 'status', 'can_manage']

    def get_can_manage(self, obj):
        return _can_manage_team(self.context, obj)


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = ['id', 'name', 'wechat_qr_code', 'created_at', 'updated_at']
        read_only_fields = ['wechat_qr_code', 'created_at', 'updated_at']


class DepartmentSerializer(serializers.ModelSerializer):
    """部门字典输出（全集团扁平）。"""

    class Meta:
        model = Department
        fields = ['id', 'name', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

    def validate(self, attrs):
        name = attrs.get('name') or (self.instance.name if self.instance else None)
        qs = Department.objects.filter(name=name)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError({'name': [f'已存在部门「{name}」']})
        return attrs
