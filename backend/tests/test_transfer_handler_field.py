"""
Tests for transfer-handler-unification：经办人字段统一——默认创建人回填、
显式值不被覆盖、四类单据导出列头、关键字搜索。
"""
import io

import openpyxl
import pytest
from rest_framework import status

EXPORT_URL = '/api/transfers/export'


def _xlsx_rows(content):
    wb = openpyxl.load_workbook(io.BytesIO(content))
    return [list(row) for row in wb.active.iter_rows(values_only=True)]


def _purchase_payload(item_id):
    return {
        '调拨日期': '2026-01-15',
        '调拨原因': '采购入库测试',
        '调出分公司': '测试分公司',
        'items': [{'item': item_id('AST-TEST-001'), '数量': 1}],
    }


def _assign_payload(item_id, department):
    return {
        '调拨日期': '2026-01-16',
        '调拨原因': '领用出库测试',
        '调出分公司': '测试分公司',
        '调入分公司': '测试分公司',
        'items': [{'item': item_id('AST-TEST-001'), '数量': 1,
                   '使用人': '张三', 'department': str(department.id)}],
    }


def _transfer_payload(item_id, second_branch):
    return {
        '调拨日期': '2026-01-17',
        '调拨原因': '调拨测试',
        '调出分公司': '测试分公司',
        '调入分公司': second_branch.name,
        'items': [{'item': item_id('AST-TEST-001'), '数量': 1}],
    }


@pytest.mark.django_db
class TestHandlerDefault:
    """建单不传/清空经办人 → 服务端回填创建人（四类单据统一口径）"""

    def test_purchase_default_fills_creator(self, authenticated_client, branch, item_id):
        resp = authenticated_client.post('/api/transfers/purchase', _purchase_payload(item_id), format='json')
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data['经办人'] == '测试管理员'
        assert resp.data['经办人'] == resp.data['创建人']

    def test_assign_default_fills_creator(self, authenticated_client, branch, item_id, department):
        resp = authenticated_client.post('/api/transfers/assign', _assign_payload(item_id, department), format='json')
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data['经办人'] == '测试管理员'

    def test_transfer_default_fills_creator(self, authenticated_client, branch, second_branch, item_id):
        resp = authenticated_client.post('/api/transfers/transfer',
                                         _transfer_payload(item_id, second_branch), format='json')
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data['经办人'] == '测试管理员'

    def test_explicit_handler_wins(self, authenticated_client, branch, item_id):
        payload = _purchase_payload(item_id)
        payload['经办人'] = '王经办'
        resp = authenticated_client.post('/api/transfers/purchase', payload, format='json')
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data['经办人'] == '王经办'
        assert resp.data['创建人'] == '测试管理员'

    def test_blank_handler_refilled_as_creator(self, authenticated_client, branch, item_id):
        """清空提交 → 回填创建人（口径：空值无意义，等于默认）"""
        payload = _purchase_payload(item_id)
        payload['经办人'] = ''
        resp = authenticated_client.post('/api/transfers/purchase', payload, format='json')
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data['经办人'] == '测试管理员'


@pytest.mark.django_db
class TestHandlerExportColumns:
    """四类导出列头统一「经办人」，取值经办人空则兜底创建人"""

    def test_purchase_export_header_unified(self, authenticated_client, branch, item_id):
        authenticated_client.post('/api/transfers/purchase', _purchase_payload(item_id), format='json')
        resp = authenticated_client.get(EXPORT_URL, {'type': 'purchase'})
        assert resp.status_code == status.HTTP_200_OK
        rows = _xlsx_rows(resp.content)
        assert '经办人' in rows[0]
        assert '采购经办人' not in rows[0]

    def test_assign_export_has_handler_column(self, authenticated_client, branch, item_id, department):
        authenticated_client.post('/api/transfers/assign', _assign_payload(item_id, department), format='json')
        resp = authenticated_client.get(EXPORT_URL, {'type': 'assign'})
        assert resp.status_code == status.HTTP_200_OK
        rows = _xlsx_rows(resp.content)
        header = rows[0]
        assert '经办人' in header
        data_row = rows[1]
        assert data_row[header.index('经办人')] == '测试管理员'

    def test_transfer_export_has_handler_column(self, authenticated_client, branch, second_branch, item_id):
        authenticated_client.post('/api/transfers/transfer',
                                  _transfer_payload(item_id, second_branch), format='json')
        resp = authenticated_client.get(EXPORT_URL, {'type': 'transfer'})
        assert resp.status_code == status.HTTP_200_OK
        rows = _xlsx_rows(resp.content)
        header = rows[0]
        assert '经办人' in header
        assert header.index('经办人') == header.index('备注') - 1
        data_row = rows[1]
        assert data_row[header.index('经办人')] == '测试管理员'


@pytest.mark.django_db
class TestHandlerKeywordSearch:
    """列表关键字搜索沿用经办人字段（重命名后口径不变）"""

    def test_keyword_matches_handler(self, authenticated_client, branch, item_id):
        payload = _purchase_payload(item_id)
        payload['经办人'] = '独一份经办'
        authenticated_client.post('/api/transfers/purchase', payload, format='json')
        resp = authenticated_client.get('/api/transfers/', {'keyword': '独一份经办'}, format='json')
        assert resp.status_code == status.HTTP_200_OK
        results = resp.data.get('results', resp.data)
        assert len(results) == 1
        assert results[0]['经办人'] == '独一份经办'
