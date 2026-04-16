from django.core.management.base import BaseCommand
from apps.users.models import User


class Command(BaseCommand):
    help = 'Create initial superuser'

    def add_arguments(self, parser):
        parser.add_argument('--phone', default='13800000000')
        parser.add_argument('--name', default='超级管理员')
        parser.add_argument('--password', default='admin123')

    def handle(self, *args, **options):
        phone = options['phone']
        user, created = User.objects.get_or_create(
            phone=phone,
            defaults={
                'name': options['name'],
                'password': options['password'],
            }
        )
        if not created:
            self.stdout.write(self.style.WARNING(f'User {phone} already exists'))
            return
        # get_or_create bypasses create_superuser, set password hash manually
        user.set_password(options['password'])
        user.role = 'admin'
        user.is_superuser = True
        user.is_staff = True
        user.save()
        self.stdout.write(self.style.SUCCESS(f'Created superuser: {phone}'))
