from rest_framework import serializers
from apps.users.models import User
from apps.users.serializers import UserSerializer


class LoginSerializer(serializers.Serializer):
    phone = serializers.CharField()
    password = serializers.CharField()

    def validate(self, data):
        phone = data.get('phone')
        password = data.get('password')
        if not phone:
            raise serializers.ValidationError({'phone': ['手机号不能为空']})
        if not password:
            raise serializers.ValidationError({'password': ['密码不能为空']})
