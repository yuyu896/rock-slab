from django.contrib.auth.password_validation import (
    NumericPasswordValidator as _NumericPasswordValidator,
    UserAttributeSimilarityValidator as _UserAttributeSimilarityValidator,
)
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


class NumericPasswordValidator(_NumericPasswordValidator):
    """纯数字密码拒绝（中文消息；内置实现消息为内联英文，故覆写转换）。"""

    def validate(self, password, user=None):
        try:
            super().validate(password, user)
        except ValidationError as e:
            raise ValidationError('密码不能是纯数字', code=e.code)


class UserAttributeSimilarityValidator(_UserAttributeSimilarityValidator):
    """与用户属性（手机号/姓名）过于相似的密码拒绝（中文消息）。

    默认 user_attributes 为 username/first_name 等，本项目自定义 User 无这些
    字段——settings 里必须显式配置 user_attributes=['phone', 'name']。
    """

    def validate(self, password, user=None):
        try:
            super().validate(password, user)
        except ValidationError as e:
            raise ValidationError(
                '密码与 %(verbose_name)s 过于相似，请更换',
                code=e.code,
                params=e.params,
            )
