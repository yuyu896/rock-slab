"""The retired role-based seed migration must be a safe no-op."""
import pytest
from django.test import TransactionTestCase

from apps.permissions.legacy_seed import seed_legacy_grants, reverse_legacy_grants
from apps.permissions.models import ManagementScope, OperationGrant


@pytest.mark.django_db
def test_legacy_seed_hooks_do_not_infer_or_remove_authorizations(branch):
    from apps.users.models import User

    user = User.objects.create_user(
        phone='13700000001', name='普通账号', password='test123456',
        role='manager', branch=branch,
    )
    grant = OperationGrant.objects.create(user=user, code='manage_assets')
    scope = ManagementScope.objects.create(user=user, branch=branch)
    ungranted = User.objects.create_user(
        phone='13700000002', name='零授权账号', password='test123456',
        role='leader', branch=branch,
    )

    seed_legacy_grants()
    reverse_legacy_grants()

    assert OperationGrant.objects.filter(pk=grant.pk, user=user).exists()
    assert ManagementScope.objects.filter(pk=scope.pk, user=user).exists()
    assert not OperationGrant.objects.filter(user=ungranted).exists()
    assert not ManagementScope.objects.filter(user=ungranted).exists()


class TestHistoricalSeedMigration(TransactionTestCase):
    """0002 neither grants by role nor deletes explicit records on reverse."""

    def test_migration_is_noop_and_reverse_preserves_existing_records(self):
        from django.db import connection
        from django.db.migrations.executor import MigrationExecutor

        before_0002 = [
            ('users', '0005_alter_user_role'),
            ('organizations', '0006_company'),
            ('permissions', '0001_initial'),
        ]
        target_0002 = [
            ('permissions', '0002_seed_grants_from_legacy_role'),
        ]
        executor = MigrationExecutor(connection)
        executor.migrate(before_0002)
        old_state = MigrationExecutor(connection).loader.project_state(before_0002)
        OldUser = old_state.apps.get_model('users', 'User')
        OldRegion = old_state.apps.get_model('organizations', 'Region')
        OldBranch = old_state.apps.get_model('organizations', 'Branch')
        OldScope = old_state.apps.get_model('permissions', 'ManagementScope')
        OldGrant = old_state.apps.get_model('permissions', 'OperationGrant')

        region = OldRegion.objects.create(name='迁移测试区域', code='SEED1', status='active')
        branch = OldBranch.objects.create(
            name='迁移测试分公司', code='SD001', region=region, status='active',
        )
        existing_user = OldUser.objects.create(
            phone='13700000001', name='已有授权', password='x',
            role='manager', status='active', region=region, branch=branch,
        )
        no_grant_user = OldUser.objects.create(
            phone='13700000002', name='无授权账号', password='x',
            role='supervisor', status='active', region=region, branch=branch,
        )
        existing_scope = OldScope.objects.create(user=existing_user, region=region)
        existing_grant = OldGrant.objects.create(user=existing_user, code='manage_assets')

        try:
            MigrationExecutor(connection).migrate(target_0002)
            migrated_state = MigrationExecutor(connection).loader.project_state(target_0002)
            MigratedScope = migrated_state.apps.get_model('permissions', 'ManagementScope')
            MigratedGrant = migrated_state.apps.get_model('permissions', 'OperationGrant')

            assert MigratedScope.objects.filter(pk=existing_scope.pk).exists()
            assert MigratedGrant.objects.filter(pk=existing_grant.pk).exists()
            assert not MigratedScope.objects.filter(user_id=no_grant_user.pk).exists()
            assert not MigratedGrant.objects.filter(user_id=no_grant_user.pk).exists()

            MigrationExecutor(connection).migrate([('permissions', '0001_initial')])
            reversed_state = MigrationExecutor(connection).loader.project_state(before_0002)
            ReversedScope = reversed_state.apps.get_model('permissions', 'ManagementScope')
            ReversedGrant = reversed_state.apps.get_model('permissions', 'OperationGrant')
            assert ReversedScope.objects.filter(pk=existing_scope.pk).exists()
            assert ReversedGrant.objects.filter(pk=existing_grant.pk).exists()
        finally:
            MigrationExecutor(connection).migrate(
                MigrationExecutor(connection).loader.graph.leaf_nodes()
            )
