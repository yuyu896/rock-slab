from datetime import date
from importlib import import_module
from types import SimpleNamespace

import pytest
from django.apps import apps
from django.db import connection

from apps.transfers.models import Transfer, TransferLine
from apps.transfers.serializers import TransferLineInputSerializer, TransferLineSerializer, TransferSerializer


@pytest.mark.django_db
def test_assign_purpose_is_not_exposed_and_note_remains_per_line(item_id, department, branch):
    data = {
        'item': item_id('AST-TEST-001'),
        '数量': 1,
        'department': str(department.id),
        '用途': '新员工配置',
        '备注': '配置到工位 12',
    }
    input_serializer = TransferLineInputSerializer(data=data)

    assert input_serializer.is_valid(), input_serializer.errors
    assert '用途' not in input_serializer.validated_data
    assert input_serializer.validated_data['备注'] == '配置到工位 12'

    transfer = Transfer.objects.create(
        调拨日期=date(2026, 10, 19),
        action_type=Transfer.ACTION_ASSIGN,
        调出分公司=branch.name,
        from_branch=branch,
        用途='历史单头用途',
        备注='历史单据备注',
    )
    line = TransferLine.objects.create(
        transfer=transfer,
        item=input_serializer.validated_data['item'],
        行号=1,
        数量=input_serializer.validated_data['数量'],
        department=input_serializer.validated_data['department'],
        备注=input_serializer.validated_data['备注'],
    )

    output = TransferLineSerializer(line).data
    assert '用途' not in output
    assert output['备注'] == '配置到工位 12'
    document_output = TransferSerializer(transfer).data
    assert '用途' not in document_output
    assert '用途' not in document_output['lines'][0]
    assert transfer.备注 == '历史单据备注'


@pytest.mark.django_db
def test_migration_backfills_assign_line_metadata_without_overwriting_existing_data(
    item_id, branch, department,
):
    from apps.organizations.models import Department

    category_id = item_id('AST-TEST-001')
    existing_department = Department.objects.create(name='行级已有部门')
    assign = Transfer.objects.create(
        调拨日期=date(2026, 10, 19),
        action_type=Transfer.ACTION_ASSIGN,
        调出分公司=branch.name,
        调出部门=department.name,
        from_branch=branch,
        用途='办公使用',
        备注='历史驳回意见：补充资产用途',
    )
    blank_assign_line = TransferLine.objects.create(
        transfer=assign,
        item_id=category_id,
        行号=1,
        数量=1,
        备注='',
    )
    populated_assign_line = TransferLine.objects.create(
        transfer=assign,
        item_id=category_id,
        行号=2,
        数量=1,
        department=existing_department,
        用途='行级用途优先',
    )
    unmatched_assign = Transfer.objects.create(
        调拨日期=date(2026, 10, 19),
        action_type=Transfer.ACTION_ASSIGN,
        调出分公司=branch.name,
        调出部门='不存在的旧部门',
        from_branch=branch,
    )
    unmatched_line = TransferLine.objects.create(
        transfer=unmatched_assign,
        item_id=category_id,
        行号=1,
        数量=1,
    )
    transfer_document = Transfer.objects.create(
        调拨日期=date(2026, 10, 19),
        action_type=Transfer.ACTION_TRANSFER,
        调出分公司=branch.name,
        from_branch=branch,
        用途='调拨用途',
        备注='调拨单头备注',
    )
    transfer_line = TransferLine.objects.create(
        transfer=transfer_document,
        item_id=category_id,
        行号=1,
        数量=1,
    )

    migration = import_module('apps.transfers.migrations.0031_assign_line_metadata')
    migration.backfill_assign_line_metadata(apps, SimpleNamespace(connection=connection))

    blank_assign_line.refresh_from_db()
    populated_assign_line.refresh_from_db()
    transfer_line.refresh_from_db()
    unmatched_line.refresh_from_db()
    assign.refresh_from_db()
    transfer_document.refresh_from_db()

    assert blank_assign_line.用途 == '办公使用'
    assert blank_assign_line.department_id == department.id
    assert blank_assign_line.备注 == ''
    assert populated_assign_line.用途 == '行级用途优先'
    assert populated_assign_line.department_id == existing_department.id
    assert unmatched_line.department is None
    assert transfer_line.用途 == ''
    assert assign.备注 == '历史驳回意见：补充资产用途'
    assert transfer_document.备注 == '调拨单头备注'
    assert TransferSerializer(transfer_document).data['用途'] == '调拨用途'
