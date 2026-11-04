"""Report permission data counts without requiring role-based seed records.

New and existing accounts may legitimately have no explicit operation grants;
system administrators receive their all-access behavior from their identity.
"""
from django.core.management.base import BaseCommand

from apps.permissions.models import ManagementScope, OperationGrant
from apps.users.models import User


class Command(BaseCommand):
    help = '报告权限数据数量；不会按岗位推断或要求预置授权'

    def handle(self, *args, **options):
        user_count = User.objects.count()
        active_count = User.objects.filter(status='active').count()
        scope_count = ManagementScope.objects.count()
        grant_count = OperationGrant.objects.count()

        self.stdout.write(f'账号数量: {user_count}（在职 {active_count}）')
        self.stdout.write(f'ManagementScope 数量: {scope_count}')
        self.stdout.write(f'OperationGrant 数量: {grant_count}')
        self.stdout.write(self.style.SUCCESS(
            '权限数据检查通过；授权为空是允许状态，权限需按账号明确设置。'
        ))
