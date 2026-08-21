from django.core.validators import RegexValidator
from rest_framework import serializers

from .models import User

phone_validator = RegexValidator(
    regex=r'^\d{11}$',
    message='手机号必须为11位数字',
)


class UserSerializer(serializers.ModelSerializer):
    phone = serializers.CharField(
        validators=[phone_validator],
    )
    password = serializers.CharField(
        write_only=True, required=False,
        help_text='用户初始密码（创建时必填；更新时不接受，改密请走 /api/auth/password/）',
    )
    branch_name = serializers.SerializerMethodField()
    region_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'phone', 'name', 'role', 'status',
            'branch', 'created_by',
            'avatar', 'system_avatar', 'password',
            'created_at', 'updated_at', 'branch_name', 'region_name',
        ]
        read_only_fields = ['created_at', 'updated_at']
        extra_kwargs = {
            'password': {'write_only': True},
        }

    def create(self, validated_data):
        # 未提供密码时回退默认初始密码 123456（临时策略，员工登录后自行修改；
        # 后续提案将改为随机密码 + 首登强制改密，见 restore-default-initial-password）
        password = validated_data.pop('password', '123456')
        user = User.objects.create_user(
            phone=validated_data['phone'],
            name=validated_data['name'],
            password=password,
            **{k: v for k, v in validated_data.items() if k not in ('phone', 'name')},
        )
        return user

    def update(self, instance, validated_data):
        # password 为 create-only：更新路径绝不接受密码字段（防账号接管）。
        # 即便误传也丢弃，绝不走 ModelSerializer 默认的 setattr 原样写入 password 列。
        validated_data.pop('password', None)
        instance = super().update(instance, validated_data)
        # status 与 is_active 联动：停用即禁用登录并失效存量 token，启用则恢复
        if instance.status == 'inactive' and instance.is_active:
            instance.is_active = False
            instance.save(update_fields=['is_active'])
        elif instance.status == 'active' and not instance.is_active:
            instance.is_active = True
            instance.save(update_fields=['is_active'])
        if instance.status == 'inactive':
            from apps.authentication.models import ExpiringToken
            ExpiringToken.objects.filter(user=instance).delete()
        return instance

    def get_branch_name(self, obj):
        return obj.branch.name if obj.branch else None

    def get_region_name(self, obj):
        # 区域归属沿树派生：branch → team → region
        if obj.branch and obj.branch.team:
            return obj.branch.team.region.name if obj.branch.team.region else None
        return None
