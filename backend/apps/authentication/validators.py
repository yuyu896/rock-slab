from django.core.exceptions import ValidationError


class MinimumLengthValidator:
    """Validate that the password meets the minimum length (default 8)."""

    def __init__(self, min_length=8):
        self.min_length = min_length

    def validate(self, password, user=None):
        if len(password) < self.min_length:
            raise ValidationError(
                '密码长度不能少于 %(min_length)d 位',
                code='password_too_short',
                params={'min_length': self.min_length},
            )

    def get_help_text(self):
        return '密码长度不能少于 %(min_length)d 位' % {'min_length': self.min_length}
