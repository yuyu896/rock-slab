"""部门字典契约测试（department-dictionary 能力，全集团扁平）。"""
import importlib
import pytest
from conftest import _client_for
from rest_framework import status


@pytest.mark.django_db
class TestDepartmentModel:
    def test_global_duplicate_rejected(self, db):
        from apps.organizations.models import Department
        from django.db import IntegrityError
        Department.objects.create(name='行政部')
        with pytest.raises(IntegrityError):
            Department.objects.create(name='行政部')


@pytest.mark.django_db
class TestDepartmentAPI:
    def _auth(self, user):
        return _client_for(user)

    def test_create_and_list(self, admin_user):
        client = self._auth(admin_user)
        resp = client.post('/api/departments/', {'name': '财务部'}, format='json')
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data['name'] == '财务部'
        resp = client.get('/api/departments/')
        assert resp.status_code == status.HTTP_200_OK

    def test_duplicate_returns_400_with_hint(self, admin_user):
        from apps.organizations.models import Department
        Department.objects.create(name='人事部')
        client = self._auth(admin_user)
        resp = client.post('/api/departments/', {'name': '人事部'}, format='json')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert '唯一' in str(resp.data) or '已存在' in str(resp.data)

    def test_create_requires_permission(self, staff_user):
        client = self._auth(staff_user)
        resp = client.post('/api/departments/', {'name': '仓库'}, format='json')
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_options_returns_full_flat_set(self, staff_user):
        from apps.organizations.models import Department
        Department.objects.create(name='行政部')
        Department.objects.create(name='市场部')
        client = self._auth(staff_user)
        resp = client.get('/api/departments/options')
        assert resp.status_code == status.HTTP_200_OK
        names = [d['name'] for d in resp.data]
        assert set(names) == {'行政部', '市场部'}
        assert len(names) == 2


@pytest.mark.django_db
class TestDepartmentFlattenMigration:
    """0009 扁平化迁移：同名合并保留最早行、FK 重指向、幂等。"""

    def _run_flatten(self):
        from django.apps import apps as global_apps
        migration = importlib.import_module(
            'apps.organizations.migrations.0009_alter_department_options_and_more'
        )
        migration.flatten_departments(global_apps, None)

    def test_merge_keeps_earliest_and_repoints_fks(self, db, monkeypatch):
        """合并逻辑单测（分组保留最早行 + 三表 FK 重指向 + 删重复）。

        迁移后 schema 的 name 全局唯一使测试库无法直造重名行（约束防的正是它），
        故以桩对象喂数据验证纯逻辑；数据库层行为由 Django 保证。
        """
        from types import SimpleNamespace
        from django.utils import timezone
        from datetime import timedelta
        from apps.organizations.models import Department
        from apps.transfers.models import TransferLine
        from apps.inventories.models import InventoryTask
        from apps.assets.models import FixedAsset

        now = timezone.now()
        old = SimpleNamespace(id='keep-1', name='行政部', created_at=now - timedelta(days=10))
        dup_a = SimpleNamespace(id='dup-1', name='行政部', created_at=now - timedelta(days=5))
        dup_b = SimpleNamespace(id='dup-2', name='行政部', created_at=now - timedelta(days=1))
        other = SimpleNamespace(id='keep-2', name='市场部', created_at=now - timedelta(days=3))
        rows = [dup_a, old, other, dup_b]  # 乱序输入，函数须按 created_at 排序保留最早

        updates = {}
        deletes = []

        class _DeptManager:
            def order_by(self, *a):
                return sorted(rows, key=lambda r: (r.created_at, r.id))

            def filter(self, **kw):
                ids = list(kw.get('id__in'))
                return SimpleNamespace(delete=lambda: deletes.append(ids))

        def _manager_for(model):
            return SimpleNamespace(
                filter=lambda **kw: SimpleNamespace(
                    update=lambda **u: updates.setdefault(model.__name__, []).append((kw, u))
                )
            )

        import apps.organizations.models as org_models
        import apps.transfers.models as trf_models
        import apps.inventories.models as inv_models
        import apps.assets.models as ast_models
        monkeypatch.setattr(Department, 'objects', _DeptManager(), raising=False)
        monkeypatch.setattr(trf_models.TransferLine, 'objects', _manager_for(TransferLine), raising=False)
        monkeypatch.setattr(inv_models.InventoryTask, 'objects', _manager_for(InventoryTask), raising=False)
        monkeypatch.setattr(ast_models.FixedAsset, 'objects', _manager_for(FixedAsset), raising=False)
        _ = org_models  # 引用占位（monkeypatch 目标经模块名取得）

        self._run_flatten()

        # 三表对每个重复 id 都重指向保留行
        for model_name in ('TransferLine', 'InventoryTask', 'FixedAsset'):
            got = {kw['department_id']: u['department_id'] for kw, u in updates[model_name]}
            assert got == {'dup-1': 'keep-1', 'dup-2': 'keep-1'}, model_name
        # 重复行被删除，保留行不动
        assert deletes == [[ 'dup-1', 'dup-2']]

    def test_flatten_noop_when_unique(self, db):
        from apps.organizations.models import Department
        Department.objects.create(name='行政部')
        Department.objects.create(name='市场部')
        self._run_flatten()
        assert Department.objects.count() == 2
