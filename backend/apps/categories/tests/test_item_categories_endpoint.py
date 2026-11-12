"""Tests for item-categories API endpoint."""
import pytest
from django.urls import reverse
from rest_framework import status
from apps.users.models import User
from apps.organizations.models import Region, Branch, Team


@pytest.fixture
def api_client():
    """Create an authenticated API client."""
    from rest_framework.test import APIClient
    return APIClient()


@pytest.fixture
def test_user(db):
    """Create a test user with valid organization structure."""
    region = Region.objects.create(name='测试大区', code='TEST')
    team = Team.objects.create(name='测试团队', region=region)
    branch = Branch.objects.create(name='测试分公司', code='TST001', team=team)

    user = User.objects.create_user(
        phone='13800000000',
        password='testpass123',
        name='测试用户',
        team=team,
        role='admin',
    )
    return user


@pytest.mark.django_db
class TestItemCategoriesEndpoint:
    """Test the /api/categories/item-categories/ endpoint."""

    def test_get_item_categories_valid_asset_category(self, api_client, test_user):
        """Valid asset_category returns corresponding item categories."""
        api_client.force_authenticate(user=test_user)
        url = reverse('category-item-categories')

        response = api_client.get(url, {'asset_category': '固定资产类'})

        assert response.status_code == status.HTTP_200_OK
        assert response.data['asset_category'] == '固定资产类'
        assert response.data['item_categories'] == ['办公设备', '电子设备', '特殊设备']

    def test_get_item_categories_all_valid_categories(self, api_client, test_user):
        """Test all valid asset categories return correct item categories."""
        api_client.force_authenticate(user=test_user)
        url = reverse('category-item-categories')

        test_cases = [
            ('固定资产类', ['办公设备', '电子设备', '特殊设备']),
            ('低值易耗品类', ['办公耗材', '清洁用品', '其他消耗品']),
            ('无形资产类', ['软件与数据']),
            ('文档资料类', ['行政文件']),
            ('特殊设备类', ['安防设备']),
            ('其他资产', ['其他']),
        ]

        for asset_category, expected_items in test_cases:
            response = api_client.get(url, {'asset_category': asset_category})
            assert response.status_code == status.HTTP_200_OK
            assert response.data['asset_category'] == asset_category
            assert response.data['item_categories'] == expected_items

    def test_get_item_categories_missing_parameter(self, api_client, test_user):
        """Missing asset_category parameter returns 400 error."""
        api_client.force_authenticate(user=test_user)
        url = reverse('category-item-categories')

        response = api_client.get(url)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'asset_category' in response.data
        assert '请提供 asset_category 参数' in response.data['asset_category'][0]

    def test_get_item_categories_empty_parameter(self, api_client, test_user):
        """Empty asset_category parameter returns 400 error."""
        api_client.force_authenticate(user=test_user)
        url = reverse('category-item-categories')

        response = api_client.get(url, {'asset_category': ''})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'asset_category' in response.data

    def test_get_item_categories_invalid_category(self, api_client, test_user):
        """Invalid asset_category returns 400 error with valid options."""
        api_client.force_authenticate(user=test_user)
        url = reverse('category-item-categories')

        response = api_client.get(url, {'asset_category': '不存在的类目'})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'asset_category' in response.data
        assert '无效的资产类目' in response.data['asset_category'][0]
        assert '固定资产类' in response.data['asset_category'][0]

    def test_get_item_categories_requires_authentication(self, api_client):
        """Endpoint requires authentication."""
        url = reverse('category-item-categories')

        response = api_client.get(url, {'asset_category': '固定资产类'})

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
