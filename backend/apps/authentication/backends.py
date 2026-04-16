import re

from django.contrib.auth.backends import ModelBackend
from rest_framework import authentication
from rest_framework import exceptions

from apps.authentication.models import ExpiringToken


class PhoneModelBackend(ModelBackend):
    """Authenticate using phone number instead of username."""

    def authenticate(self, request, phone=None, password=None, **kwargs):
        if not phone or not re.match(r'^\d{11}$', phone):
            return None
        from apps.users.models import User
        try:
            user = User.objects.get(phone=phone)
        except User.DoesNotExist:
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None


class ExpiringTokenAuthentication(authentication.TokenAuthentication):
    """Token authentication that checks expiration."""

    model = ExpiringToken

    def authenticate_credentials(self, key):
        try:
            token = self.model.objects.select_related('user').get(key=key)
        except self.model.DoesNotExist:
            raise exceptions.AuthenticationFailed('无效的认证令牌')

        if not token.user.is_active:
            raise exceptions.AuthenticationFailed('用户已被禁用')

        if token.is_expired:
            raise exceptions.AuthenticationFailed('认证令牌已过期，请重新登录')

        return (token.user, token)
