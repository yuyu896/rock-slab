"""Organization tests: branch code format validation."""
import pytest
from rest_framework import status


@pytest.mark.django_db
class TestBranchCodeValidation:
    def test_create_branch_valid_code(self, authenticated_client, region):
        resp = authenticated_client.post('/api/branches/', {
            'name': '上海分公司', 'code': 'SH001', 'region': region.id, 'status': 'active',
        })
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data['code'] == 'SH001'

    def test_create_branch_lowercase_auto_uppercase(self, authenticated_client, region):
        resp = authenticated_client.post('/api/branches/', {
            'name': '北京分公司', 'code': 'bj001', 'region': region.id, 'status': 'active',
        })
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data['code'] == 'BJ001'

    def test_create_branch_stripped_whitespace(self, authenticated_client, region):
        resp = authenticated_client.post('/api/branches/', {
            'name': '广州分公司', 'code': ' GZ001 ', 'region': region.id, 'status': 'active',
        })
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data['code'] == 'GZ001'

    def test_create_branch_invalid_format_chinese(self, authenticated_client, region):
        resp = authenticated_client.post('/api/branches/', {
            'name': '测试分公司', 'code': '上海001', 'region': region.id, 'status': 'active',
        })
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_branch_invalid_format_short_number(self, authenticated_client, region):
        resp = authenticated_client.post('/api/branches/', {
            'name': '测试分公司', 'code': 'SH01', 'region': region.id, 'status': 'active',
        })
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_branch_invalid_format_dash(self, authenticated_client, region):
        resp = authenticated_client.post('/api/branches/', {
            'name': '测试分公司', 'code': 'SH-001', 'region': region.id, 'status': 'active',
        })
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_branch_4_letter_prefix(self, authenticated_client, region):
        resp = authenticated_client.post('/api/branches/', {
            'name': '哈尔滨分公司', 'code': 'HRB001', 'region': region.id, 'status': 'active',
        })
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data['code'] == 'HRB001'
