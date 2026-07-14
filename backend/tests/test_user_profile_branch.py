"""UserSerializer 返回分公司/区域名称（个人中心所属分公司显示修复）测试。"""
import pytest


@pytest.mark.django_db
class TestUserBranchName:
    def test_serializer_returns_branch_name(self, branch):
        from apps.users.models import User
        from apps.users.serializers import UserSerializer
        user = User.objects.create_user(
            phone='13900088888', name='有分公司', password='test123456',
            role='staff', status='active', branch=branch, region=branch.region,
        )
        data = UserSerializer(user).data
        assert data['branch_name'] == branch.name
        assert data['region_name'] == branch.region.name

    def test_serializer_branch_name_none_when_unset(self, db):
        from apps.users.models import User
        from apps.users.serializers import UserSerializer
        user = User.objects.create_user(
            phone='13900077777', name='无分公司', password='test123456',
            role='staff', status='active',
        )
        data = UserSerializer(user).data
        assert data['branch_name'] is None
        assert data['region_name'] is None
