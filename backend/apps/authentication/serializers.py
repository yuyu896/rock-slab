import re
from rest_framework import serializers


class LoginSerializer(serializers.Serializer):
    phone = serializers.CharField(required=True, error_messages={'required': '手机号不能为空', 'blank': '手机号不能为空'})
    password = serializers.CharField(required=True, error_messages={'required': '密码不能为空', 'blank': '密码不能为空'})

    def validate_phone(self, value):
        if not re.match(r'^\d{11}$', value):
            raise serializers.ValidationError('请输入有效的11位手机号')
        return value
