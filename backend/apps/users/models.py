from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.conf import settings
from core.models import UUIDModel, TimestampedModel


class UserManager(BaseUserManager):
    def create_user(self, phone, name, password=None, **extra_fields):
        if not phone:
            raise ValueError('Phone number is required')
        user = self.model(phone=phone, name=name, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone, name, password=None, **extra_fields):
        extra_fields.setdefault('role', 'admin')
        extra_fields.setdefault('status', 'active')
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(phone, name, password, **extra_fields)


class User(UUIDModel, TimestampedModel, AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = [
        ('admin', 'admin'),
        ('manager', 'manager'),
        ('supervisor', 'supervisor'),
        ('leader', 'leader'),
        ('staff', 'staff'),
    ]
    STATUS_CHOICES = [
        ('active', 'active'),
        ('inactive', 'inactive'),
    ]
    SYSTEM_AVATAR_CHOICES = [f'geo-{i}' for i in range(1, 11)]

    phone = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='staff')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    system_avatar = models.CharField(
        max_length=20, null=True, blank=True,
        verbose_name='系统预设头像标识',
    )
    branch = models.ForeignKey(
        'organizations.Branch', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='users',
    )
    region = models.ForeignKey(
        'organizations.Region', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='users',
    )
    leader = models.ForeignKey(
        'self', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='subordinates',
    )
    team = models.ForeignKey(
        'organizations.Team', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='members',
        verbose_name='所属行政组',
    )
    created_by = models.ForeignKey(
        'self', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='created_users',
    )
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True, verbose_name='头像')

    objects = UserManager()

    USERNAME_FIELD = 'phone'
    REQUIRED_FIELDS = ['name']

    class Meta:
        db_table = 'users'
        ordering = ['-created_at']
