from rest_framework import serializers
from django.core.validators import RegexValidator
from .models import Region, Branch, Team, Company, BRANCH_CODE_REGEX, Department


def _assert_appointment_admin_only(serializer, attrs, field):
    """任命/免任仅 admin：任命即授权，manage_organizations 不隐含任命权（防提权链）。

    值未变（含 null→null）或未携带该字段的普通节点编辑放行。
    """
    request = serializer.context.get('request')
    user = getattr(request, 'user', None)
    if user is None or not getattr(user, 'is_authenticated', False) or user.role == 'admin':
        return
    if field not in attrs:
        return
    current = getattr(serializer.instance, field, None) if serializer.instance else None
    if attrs[field] != current:
        raise serializers.ValidationError({field: ['任命/免任仅系统管理员可操作']})


class RegionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Region
        fields = [
            'id', 'name', 'code', 'manager', 'status',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']

    def validate(self, attrs):
        _assert_appointment_admin_only(self, attrs, 'manager')
        return attrs


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


class TeamSerializer(serializers.ModelSerializer):
    region_name = serializers.CharField(source='region.name', read_only=True)
    leader_name = serializers.CharField(source='leader.name', read_only=True, default=None)
    member_count = serializers.SerializerMethodField()

    class Meta:
        model = Team
        fields = [
            'id', 'name', 'region', 'region_name',
            'leader', 'leader_name', 'member_count',
            'status', 'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']

    def get_member_count(self, obj):
        from apps.users.models import User
        return User.objects.filter(branch__team=obj).count()

    def validate(self, attrs):
        _assert_appointment_admin_only(self, attrs, 'leader')
        return attrs


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = ['id', 'name', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


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
