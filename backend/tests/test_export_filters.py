"""
Tests for export endpoints respecting query filters (export-respect-filters).
"""
import io

import pytest
import openpyxl

from apps.transfers.models import Transfer
from conftest import _client_for


def _xlsx_rows(content):
    wb = openpyxl.load_workbook(io.BytesIO(content))
    return list(wb.active.iter_rows(values_only=True))


@pytest.mark.django_db
class TestStockExportFilters:
    """台账导出遵循筛选（Asset 导出已随第三刀退役，台账承接导出契约）。"""

    def test_export_respects_branch_keyword(self, supervisor_user, branch, second_branch):
        from apps.assets.services import ledger
        from apps.categories.models import Category
        for br, code, cat, name in [
            (branch, 'EF-1', '固定资产', '办公椅甲'),
            (branch, 'EF-2', '耗材', '办公椅乙'),
            (second_branch, 'EF-3', '固定资产', '办公椅丙'),
        ]:
            item, _ = Category.objects.get_or_create(
                asset_code=code,
                defaults={'asset_category': cat, 'item_category': '办公设备',
                          'asset_name': name, 'unit': '件'},
            )
            ledger.apply_adjustment(br, item, ledger.COLUMN_STOCK, 1, '造数')

        client = _client_for(supervisor_user)
        resp = client.get('/api/assets/summary/export', {
            'branch': branch.name, 'category': '固定资产', 'keyword': '办公椅',
        })
        assert resp.status_code == 200
        rows = _xlsx_rows(resp.content)
        codes = [r[2] for r in rows[1:]]  # 第 3 列为资产编号
        assert codes == ['EF-1']



@pytest.mark.django_db
class TestTransferExportFilters:
    def test_export_respects_type_and_keyword(self, authenticated_client, branch):
        from apps.categories.models import Category
        from apps.transfers.models import TransferLine

        def make(code, name, action):
            # P2：品目身份在字典、数量在明细行；keyword 经明细行联品目名称命中
            item = Category.objects.create(
                asset_category='测试类目', item_category='测试分类',
                asset_name=name, asset_code=code, unit='把',
            )
            t = Transfer.objects.create(
                调拨日期='2026-08-19', 调出分公司=branch.name, from_branch=branch,
                action_type=action,
            )
            TransferLine.objects.create(transfer=t, item=item, 行号=1, 数量=1)
            return t

        make('TE-1', '会议椅', Transfer.ACTION_RECOVERY)
        make('TE-2', '会议桌', Transfer.ACTION_RECOVERY)
        make('TE-3', '会议椅', Transfer.ACTION_ASSIGN)

        resp = authenticated_client.get('/api/transfers/export', {
            'type': 'recovery', 'keyword': '会议椅',
        })
        assert resp.status_code == 200
        rows = _xlsx_rows(resp.content)
        codes = [r[2] for r in rows[1:]]  # 回收模板：序号、分公司、资产编号（第 3 列）
        assert codes == ['TE-1']


@pytest.mark.django_db
class TestKeywordOperatorSearch:
    """流转 keyword 搜经办人（第 24 案）：经办人/创建人 OR 匹配。"""

    def test_keyword_matches_operator(self, authenticated_client, branch):
        from apps.transfers.models import Transfer
        import datetime
        Transfer.objects.create(
            单据编号='KW-OP-001', 调拨日期=datetime.date(2026, 9, 13),
            action_type='assign', 审批状态='待审批',
            from_branch=branch, 调出分公司=branch.name, 创建人='陈靖萱', 经办人='',
        )
        Transfer.objects.create(
            单据编号='KW-OP-002', 调拨日期=datetime.date(2026, 9, 13),
            action_type='purchase', 审批状态='待审批',
            to_branch=branch, 调入分公司=branch.name, 创建人='别人', 经办人='潘梦洁',
        )
        r1 = authenticated_client.get('/api/transfers/?keyword=陈靖萱')
        assert r1.data['count'] >= 1
        assert any(t['单据编号'] == 'KW-OP-001' for t in r1.data['results'])
        r2 = authenticated_client.get('/api/transfers/?keyword=潘梦洁')
        assert any(t['单据编号'] == 'KW-OP-002' for t in r2.data['results'])
