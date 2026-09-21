"""采购单撤回（待审批→草稿，仅创建人）+ 草稿可编辑 测试。"""
import pytest
from conftest import _client_for


def _make_purchase(client, code, branch, item_id, status=None, draft=False):
    payload = {
        '调拨日期': '2026-09-19', '调出分公司': branch.name,
        'items': [{'item': item_id(code), '数量': 2, '供应商': '甲供应商'}],
    }
    if draft:
        payload['draft'] = True
    resp = client.post('/api/transfers/purchase', payload, format='json')
    assert resp.status_code == 201
    from apps.transfers.models import Transfer
    t = Transfer.objects.get(id=resp.data['id'])
    if status:
        t.审批状态 = status
        t.save(update_fields=['审批状态'])
    return t


@pytest.mark.django_db
class TestPurchaseWithdraw:
    def test_creator_withdraws_pending(self, admin_user, branch, item_id):
        client = _client_for(admin_user)
        t = _make_purchase(client, 'PUR-001', branch, item_id, status='待审批')
        resp = client.post(f'/api/transfers/{t.id}/withdraw', format='json')
        assert resp.status_code == 200
        assert resp.data['审批状态'] == '草稿'
        t.refresh_from_db()
        assert t.审批状态 == '草稿'

    def test_non_creator_rejected(self, admin_user, branch, item_id, db):
        from django.contrib.auth import get_user_model
        other_admin = get_user_model().objects.create_user(
            phone='13900000009', name='二号管理员', password='test123456',
            role='admin', status='active',
        )
        t = _make_purchase(_client_for(admin_user), 'APR-001', branch, item_id, status='待审批')
        resp = _client_for(other_admin).post(f'/api/transfers/{t.id}/withdraw', format='json')
        assert resp.status_code == 400
        t.refresh_from_db()
        assert t.审批状态 == '待审批'

    @pytest.mark.parametrize('status', ['草稿', '已通过', '已驳回', '已入库'])
    def test_non_pending_status_rejected(self, admin_user, branch, item_id, status):
        client = _client_for(admin_user)
        t = _make_purchase(client, 'APR-002', branch, item_id, status=status)
        resp = client.post(f'/api/transfers/{t.id}/withdraw', format='json')
        assert resp.status_code == 400

    def test_withdraw_then_edit_then_submit_full_chain(self, admin_user, branch, item_id):
        from apps.assets.models import AssetStock
        client = _client_for(admin_user)
        t = _make_purchase(client, 'APR-003', branch, item_id, status='待审批')
        stock_before = list(AssetStock.objects.values('id', '在库数量'))

        assert client.post(f'/api/transfers/{t.id}/withdraw', format='json').status_code == 200
        t.refresh_from_db()
        assert t.审批状态 == '草稿'

        # 草稿可编辑：改数量与行级供应商
        resp = client.patch(f'/api/transfers/{t.id}', {
            'items': [{'item': item_id('APR-003'), '数量': 5, '供应商': '乙供应商'}],
        }, format='json')
        assert resp.status_code == 200
        line = t.lines.get(行号=1)
        assert line.数量 == 5
        assert line.供应商 == '乙供应商'

        # 草稿重新提交进入审批流
        resp = client.post(f'/api/transfers/{t.id}/submit', format='json')
        assert resp.status_code == 200
        assert resp.data['审批状态'] == '待审批'

        # 全程未触碰台账
        assert list(AssetStock.objects.values('id', '在库数量')) == stock_before

    def test_draft_directly_editable(self, admin_user, branch, item_id):
        client = _client_for(admin_user)
        t = _make_purchase(client, 'PUR-sup', branch, item_id, draft=True)
        assert t.审批状态 == '草稿'
        resp = client.patch(f'/api/transfers/{t.id}', {
            'items': [{'item': item_id('PUR-sup'), '数量': 3, '供应商': '丙供应商'}],
        }, format='json')
        assert resp.status_code == 200
        t.refresh_from_db()
        assert t.lines.get(行号=1).数量 == 3

    def _same_name_user(self, name):
        from django.contrib.auth import get_user_model
        return get_user_model().objects.create_user(
            phone='13900000077', name=name, password='test123456',
            role='admin', status='active',
        )

    def test_same_name_different_account_rejected(self, admin_user, branch, item_id):
        """本修复核心场景：姓名相同、账号不同 → 不可撤回（旧姓名比对会误放）。"""
        same_name = self._same_name_user(admin_user.name)
        t = _make_purchase(_client_for(admin_user), 'APR-001', branch, item_id, status='待审批')
        resp = _client_for(same_name).post(f'/api/transfers/{t.id}/withdraw', format='json')
        assert resp.status_code == 400
        t.refresh_from_db()
        assert t.审批状态 == '待审批'

    def test_null_created_by_rejected(self, admin_user, branch, item_id):
        """回填不了的存量行（created_by 为空）严格拒绝。"""
        from apps.transfers.models import Transfer
        t = _make_purchase(_client_for(admin_user), 'APR-002', branch, item_id, status='待审批')
        Transfer.objects.filter(id=t.id).update(created_by=None)
        resp = _client_for(admin_user).post(f'/api/transfers/{t.id}/withdraw', format='json')
        assert resp.status_code == 400
        t.refresh_from_db()
        assert t.审批状态 == '待审批'

    def test_can_withdraw_field(self, admin_user, branch, item_id):
        """序列化 canWithdraw：创建人待审批 True；同名他人/草稿态 False。"""
        client = _client_for(admin_user)
        t = _make_purchase(client, 'APR-003', branch, item_id, status='待审批')

        resp = client.get(f'/api/transfers/{t.id}', format='json')
        assert resp.status_code == 200
        assert resp.data['canWithdraw'] is True

        same_name = self._same_name_user(admin_user.name)
        resp = _client_for(same_name).get(f'/api/transfers/{t.id}', format='json')
        assert resp.data['canWithdraw'] is False

        assert client.post(f'/api/transfers/{t.id}/withdraw', format='json').status_code == 200
        resp = client.get(f'/api/transfers/{t.id}', format='json')
        assert resp.data['canWithdraw'] is False


@pytest.mark.django_db
class TestCreatorBackfill:
    """迁移回填：唯一命中才填，重名/无匹配留空。"""

    def _run_backfill(self):
        import importlib
        from django.apps import apps as global_apps
        migration = importlib.import_module(
            'apps.transfers.migrations.0020_transfer_created_by_and_more'
        )
        migration.backfill_created_by(global_apps, None)

    def _make_transfer(self, creator_str, branch):
        from apps.transfers.models import Transfer
        return Transfer.objects.create(
            action_type=Transfer.ACTION_PURCHASE,
            调拨日期='2026-09-21',
            调入分公司=branch.name,
            to_branch=branch,
            审批状态='已通过',
            创建人=creator_str,
        )

    def test_unique_name_backfilled(self, db, branch):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        User.objects.create_user(phone='13700000001', name='唯一张三', password='x', role='leader', status='active')
        t = self._make_transfer('唯一张三', branch)
        self._run_backfill()
        t.refresh_from_db()
        assert t.created_by is not None
        assert t.created_by.name == '唯一张三'

    def test_duplicate_name_skipped(self, db, branch):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        User.objects.create_user(phone='13700000002', name='重复李四', password='x', role='leader', status='active')
        User.objects.create_user(phone='13700000003', name='重复李四', password='x', role='leader', status='active')
        t = self._make_transfer('重复李四', branch)
        self._run_backfill()
        t.refresh_from_db()
        assert t.created_by is None

    def test_no_match_skipped(self, db, branch):
        t = self._make_transfer('查无此人', branch)
        self._run_backfill()
        t.refresh_from_db()
        assert t.created_by is None

    def test_phone_backfilled(self, db, branch):
        """创建人存的是手机号（建单时姓名为空的兜底路径）也能回填。"""
        from django.contrib.auth import get_user_model
        User = get_user_model()
        u = User.objects.create_user(phone='13700000004', name='手机王五', password='x', role='leader', status='active')
        t = self._make_transfer('13700000004', branch)
        self._run_backfill()
        t.refresh_from_db()
        assert t.created_by == u
