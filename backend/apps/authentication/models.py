from django.conf import settings
from django.db import models
from django.utils import timezone
from rest_framework.authtoken.models import Token


class ExpiringToken(Token):
    """Token model with expiration support."""
    expires_at = models.DateTimeField(verbose_name='过期时间', default=None)

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timezone.timedelta(
                days=getattr(settings, 'TOKEN_EXPIRATION_DAYS', 30)
            )
        return super().save(*args, **kwargs)

    @property
    def is_expired(self):
        return timezone.now() >= self.expires_at

    class Meta:
        verbose_name = 'Token'
        verbose_name_plural = 'Tokens'
