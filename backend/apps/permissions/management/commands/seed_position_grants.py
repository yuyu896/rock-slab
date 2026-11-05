"""Deprecated command kept as a safe compatibility entry point.

Permissions are assigned explicitly per account. A position must not grant or
remove operation permissions or data scopes.
"""
from django.core.management.base import BaseCommand, CommandError

from apps.permissions.models import ManagementScope, OperationGrant
from apps.users.models import User


class Command(BaseCommand):
    help = '已停用：岗位不再自动授予权限；此命令不会修改授权或数据范围'

    def add_arguments(self, parser):
        parser.add_argument(
            '--apply', action='store_true',
            help='已停用；使用此参数会报错，不会写入任何数据',
        )

    def handle(self, *args, **options):
        if options['apply']:
            raise CommandError(
                'seed_position_grants 已停用：岗位不再自动授予权限。'
                '请在权限分配页面为员工明确授予操作权限和数据范围。未修改任何数据。'
            )

        active_users = User.objects.filter(status='active').count()
        scopes = ManagementScope.objects.count()
        grants = OperationGrant.objects.count()
        self.stdout.write(
            self.style.WARNING(
                'seed_position_grants 已停用；岗位不会自动授予或撤销权限。'
                f'当前在职账号 {active_users} 个，已有数据范围 {scopes} 条、操作授权 {grants} 条。'
            )
        )
