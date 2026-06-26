import os
import sys

from django.core.management.base import BaseCommand
from apps.users.models import User


class Command(BaseCommand):
    help = 'Create initial superuser (credentials must be provided explicitly)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--phone',
            default=None,
            help='超级管理员手机号（或环境变量 SUPERUSER_PHONE）',
        )
        parser.add_argument('--name', default='超级管理员')
        parser.add_argument(
            '--password',
            default=None,
            help='超级管理员密码（或环境变量 SUPERUSER_PASSWORD）',
        )

    def handle(self, *args, **options):
        phone = options['phone'] or os.environ.get('SUPERUSER_PHONE')
        password = options['password'] or os.environ.get('SUPERUSER_PASSWORD')

        if not phone or not password:
            self.stderr.write(self.style.ERROR(
                '必须显式提供手机号与密码：使用 --phone/--password 参数，'
                '或设置环境变量 SUPERUSER_PHONE / SUPERUSER_PASSWORD。'
            ))
            sys.exit(1)

        user, created = User.objects.get_or_create(
            phone=phone,
            defaults={'name': options['name']},
        )
        if not created:
            self.stdout.write(self.style.WARNING(f'User {phone} already exists'))
            return

        # get_or_create bypasses create_superuser, set password hash manually
        user.set_password(password)
        user.role = 'admin'
        user.is_superuser = True
        user.is_staff = True
        user.save()
        self.stdout.write(self.style.SUCCESS(f'Created superuser: {phone}'))
