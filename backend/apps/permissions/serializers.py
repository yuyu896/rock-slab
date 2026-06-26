from rest_framework import serializers
from apps.organizations.models import Region, Branch, Team
from apps.users.models import User
from .models import ManagementScope, OperationGrant
from .operations import OPERATIONS


class OperationGrantSerializer(serializers.ModelSerializer):
    label = serializers.SerializerMethodField()

    class Meta:
        model = OperationGrant
        fields = ['id', 'user', 'code', 'label', 'created_at']
        read_only_fields = ['id', 'created_at']

    def get_label(self, obj):
        return OPERATIONS.get(obj.code, obj.code)


class ManagementScopeSerializer(serializers.ModelSerializer):
    """管理授权（组织节点）。写入时：is_all_data（全部数据）或 region/branch/team 三选一。"""

    # 兼容前端 camelCase 字段
    isAllData = serializers.BooleanField(source='is_all_data', required=False)

    class Meta:
        model = ManagementScope
        fields = ['id', 'user', 'is_all_data', 'isAllData', 'region', 'branch', 'team', 'created_at']
        read_only_fields = ['id', 'created_at']

    def validate(self, attrs):
        # 合并 instance 与传入数据，便于更新场景校验
        is_all_data = attrs.get(
            'is_all_data', getattr(self.instance, 'is_all_data', False)
        )
        data = {
            'region': attrs.get('region', getattr(self.instance, 'region', None)),
            'branch': attrs.get('branch', getattr(self.instance, 'branch', None)),
            'team': attrs.get('team', getattr(self.instance, 'team', None)),
        }
        nodes = [n for n in (data['region'], data['branch'], data['team']) if n is not None]
        if is_all_data:
            if nodes:
                raise serializers.ValidationError('「全部数据」授权与具体组织节点互斥')
            # 每用户至多一条「全部数据」授权（DB 约束为兜底，这里返回友好 400）
            user = attrs.get('user', getattr(self.instance, 'user', None))
            qs = ManagementScope.objects.filter(user=user, is_all_data=True)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError('该员工已有「全部数据」授权，每员工至多一条')
        else:
            if len(nodes) == 0:
                raise serializers.ValidationError('必须指定一个组织节点（region / branch / team 三选一）或勾选 is_all_data')
            if len(nodes) > 1:
                raise serializers.ValidationError('至多指定一个组织节点（region / branch / team 三选一）')
        return attrs


class UserPermissionSummarySerializer(serializers.ModelSerializer):
    """某用户的授权摘要（供前端判断权限）。"""

    management_scopes = ManagementScopeSerializer(many=True, read_only=True)
    operations = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'name', 'phone', 'role', 'management_scopes', 'operations']

    def get_operations(self, obj):
        return list(obj.operation_grants.values_list('code', flat=True))


class OperationCatalogSerializer(serializers.Serializer):
    """操作码目录（供前端勾选）。"""

    code = serializers.CharField()
    label = serializers.CharField()
