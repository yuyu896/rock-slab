import re

from django.contrib.auth.backends import ModelBackend


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
