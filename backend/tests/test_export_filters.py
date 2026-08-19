"""
Tests for export endpoints respecting query filters (export-respect-filters).
"""
import io

import pytest
import openpyxl

from apps.assets.models import Asset
from apps.transfers.models import Transfer
from conftest import _client_for


def _xlsx_rows(content):
    wb = openpyxl.load_workbook(io.BytesIO(content))
    return list(wb.active.iter_rows(values_only=True))


@pytest.mark.django_db
class TestAssetExportFilters:
    def test_export_respects_branch_category_keyword(self, supervisor_user, branch, second_branch):
        def make(seq, br, code, cat, name):
            return Asset.objects.create(
                序号=seq, 分公司=br.name, 分公司编号=br.code, branch=br,
                资产编号=code, 资产类目=cat, 物品分类='办公设备',
                资产名称=name, 数量=1, 当前状态='在库',
            )

        make(1, branch, 'EF-1', '固定资产', '办公椅甲')
        make(2, branch, 'EF-2', '耗材', '办公椅乙')
        make(3, second_branch, 'EF-3', '固定资产', '办公椅丙')

        client = _client_for(supervisor_user)
        resp = client.get('/api/assets/export', {
            'branch': branch.name, 'category': '固定资产', 'keyword': '办公椅',
        })
        assert resp.status_code == 200
        rows = _xlsx_rows(resp.content)
        codes = [r[2] for r in rows[1:]]  # 第 3 列为资产编号
        assert codes == ['EF-1']


@pytest.mark.django_db
class TestTransferExportFilters:
    def test_export_respects_type_and_keyword(self, authenticated_client, branch):
        def make(code, name, action):
            return Transfer.objects.create(
                调拨日期='2026-08-19', 调出分公司=branch.name, from_branch=branch,
                资产编号=code, 资产名称=name, 调拨数量=1, action_type=action,
            )

        make('TE-1', '会议椅', Transfer.ACTION_RECOVERY)
        make('TE-2', '会议桌', Transfer.ACTION_RECOVERY)
        make('TE-3', '会议椅', Transfer.ACTION_ASSIGN)

        resp = authenticated_client.get('/api/transfers/export', {
            'type': 'recovery', 'keyword': '会议椅',
        })
        assert resp.status_code == 200
        rows = _xlsx_rows(resp.content)
        codes = [r[2] for r in rows[1:]]  # 回收模板：分公司、资产编号（第 3 列）
        assert codes == ['TE-1']
