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
        help_text='用户初始密码（创建时必填）',
    )

    class Meta:
        model = User
        fields = [
            'id', 'phone', 'name', 'role', 'status',
            'branch', 'region', 'leader', 'team', 'created_by',
            'avatar', 'system_avatar', 'password',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']
        extra_kwargs = {
            'password': {'write_only': True},
        }

    def create(self, validated_data):
        password = validated_data.pop('password', '123456')
        user = User.objects.create_user(
            phone=validated_data['phone'],
            name=validated_data['name'],
            password=password,
            **{k: v for k, v in validated_data.items() if k not in ('phone', 'name')},
        )
        return user
