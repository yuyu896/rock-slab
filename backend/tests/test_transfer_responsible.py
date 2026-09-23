"""
Tests for transfer-responsible-unify：调出负责人退役并入经办人（迁移回放验证）、
调拨导出列、经办人不经手调出负责人。
"""
import io

import openpyxl
import pytest
from rest_framework import status

MIG_HEAD = '0024_alter_transfer_经办人'
MIG_PRE_DROP = '0021_rename_采购经办人_transfer_经办人'


def _xlsx_rows(content):
    wb = openpyxl.load_workbook(io.BytesIO(content))
    return [list(row) for row in wb.active.iter_rows(values_only=True)]


@pytest.mark.django_db(transaction=True)
class TestOutgoingResponsibleMergeMigration:
    """回放到删列前状态造数，前进验证合并口径（空取调出负责人/已有值不覆盖/非调拨不动）"""

    def test_merge_fills_empty_and_keeps_existing(self, branch):
        from django.db import connection
        from django.db.migrations.executor import MigrationExecutor

        executor = MigrationExecutor(connection)
        executor.loader.build_graph()
        executor.migrate([('transfers', MIG_PRE_DROP)])
        old = executor.loader.project_state([('transfers', MIG_PRE_DROP)]).apps.get_model('transfers', 'Transfer')
        old.objects.create(action_type='transfer', 调拨日期='2026-01-01', 经办人='', 调出负责人='王调出')
        old.objects.create(action_type='transfer', 调拨日期='2026-01-02', 经办人='李经办', 调出负责人='王调出')
        old.objects.create(action_type='transfer', 调拨日期='2026-01-03', 经办人='', 调出负责人='')
        old.objects.create(action_type='purchase', 调拨日期='2026-01-04', 经办人='', 调出负责人='不该动')

        executor.loader.build_graph()
        executor.migrate([('transfers', MIG_HEAD)])

        from apps.transfers.models import Transfer
        assert '调出负责人' not in [f.name for f in Transfer._meta.fields]
        t1 = Transfer.objects.get(调拨日期='2026-01-01')
        assert t1.经办人 == '王调出'
        t2 = Transfer.objects.get(调拨日期='2026-01-02')
        assert t2.经办人 == '李经办'
        t3 = Transfer.objects.get(调拨日期='2026-01-03')
        assert t3.经办人 == ''
        t4 = Transfer.objects.get(调拨日期='2026-01-04')
        assert t4.经办人 == ''


@pytest.mark.django_db
class TestTransferExportColumns:
    def test_export_has_no_outgoing_responsible(self, authenticated_client, branch, second_branch, item_id):
        payload = {
            '调拨日期': '2026-01-17',
            '调拨原因': '调拨测试',
            '调出分公司': '测试分公司',
            '调入分公司': second_branch.name,
            'items': [{'item': item_id('AST-TEST-001'), '数量': 1}],
        }
        resp = authenticated_client.post('/api/transfers/transfer', payload, format='json')
        assert resp.status_code == status.HTTP_201_CREATED

        resp = authenticated_client.get('/api/transfers/export', {'type': 'transfer'})
        assert resp.status_code == status.HTTP_200_OK
        rows = _xlsx_rows(resp.content)
        header = rows[0]
        assert '调出负责人' not in header
        assert '调入负责人' in header
        assert '经办人' in header
        assert header.index('经办人') == header.index('备注') - 1

    def test_template_headers_drop_outgoing_responsible(self, authenticated_client):
        resp = authenticated_client.get('/api/transfers/template', {'type': 'transfer'})
        assert resp.status_code == status.HTTP_200_OK
        rows = _xlsx_rows(resp.content)
        assert rows[0] == ['调拨日期', '调出分公司', '调出部门', '调入分公司', '调入部门',
                           '资产编号', '资产名称', '规格型号', '调拨数量', '调拨原因',
                           '调入负责人', '备注']
