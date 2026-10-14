"""Production cleanup guard for the two confirmed Yangzhou test assets."""
import datetime
from decimal import Decimal
from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.assets.models import AssetStock, FixedAsset, InstanceSequence
from apps.assets.services import ledger
from apps.categories.models import Category
from apps.notifications.models import ApprovalCC, Notification
from apps.organizations.models import Branch
from apps.transfers.models import Transfer, TransferLine, TransferLineInstance


def _item(code):
    item, _ = Category.objects.get_or_create(
        asset_code=code,
        defaults={
            'asset_category': '测试类目', 'item_category': '测试分类',
            'asset_name': f'品目 {code}', 'unit': '个',
            'management_type': 'instance',
        },
    )
    if item.management_type != 'instance':
        item.management_type = 'instance'
        item.save(update_fields=['management_type'])
    return item


@pytest.fixture
def yangzhou(team):
    return Branch.objects.create(name='扬州分公司', code='YZ001', team=team, status='active')


def _purchase(branch, doc_no, rows):
    transfer = Transfer.build(
        'purchase',
        {
            '调拨日期': datetime.date(2026, 10, 10),
            '审批状态': '已入库',
            '单据编号': doc_no,
            '调入分公司': branch.name,
            '创建人': '测试',
        },
        所属分公司=branch,
    )
    transfer.save()
    for line_no, (item, quantity, price, amount) in enumerate(rows, start=1):
        TransferLine.objects.create(
            transfer=transfer,
            item=item,
            行号=line_no,
            数量=quantity,
            单价=price,
            金额=amount,
        )
    ledger.apply_document(transfer)
    return transfer


def _create_targets(branch):
    item1 = _item('A-a00001')
    single_doc = _purchase(
        branch,
        'CG20260916-007',
        [(item1, 1, Decimal('100.00'), Decimal('100.00'))],
    )

    item2 = _item('A-a00007')
    other_items = [_item(f'YZ-EXTRA-{i}') for i in range(1, 7)]
    rows = [(item2, 42, Decimal('10.00'), Decimal('420.00'))]
    rows.extend((item, 1, None, None) for item in other_items)
    multi_doc = _purchase(branch, 'CG20251007-002', rows)
    return single_doc, multi_doc, item1, item2


def _run(*args):
    output = StringIO()
    call_command('prod_data_fix_yz_assets', *args, stdout=output)
    return output.getvalue()


@pytest.mark.django_db
def test_dry_run_previews_without_mutating(yangzhou):
    single_doc, multi_doc, item1, item2 = _create_targets(yangzhou)

    output = _run()

    assert 'dry-run 预览' in output
    assert 'CG20260916-007' in output
    assert 'CG20251007-002' in output
    assert '金额 420.00 → 410.00' in output
    assert 'A-a00001-YZ001-1' in output
    assert 'A-a00007-YZ001-42' in output
    assert FixedAsset.objects.filter(branch=yangzhou).count() == 49
    assert single_doc.pk and multi_doc.pk
    assert AssetStock.objects.get(branch=yangzhou, item=item1).在库数量 == 1
    assert AssetStock.objects.get(branch=yangzhou, item=item2).在库数量 == 42


@pytest.mark.django_db
def test_apply_deletes_targets_and_preserves_purchase_history(yangzhou, admin_user):
    single_doc, multi_doc, item1, item2 = _create_targets(yangzhou)
    single_target = FixedAsset.objects.get(birth_line__transfer=single_doc)
    multi_target = FixedAsset.objects.get(内部编号='A-a00007-YZ001-42')
    single_line_id = single_target.birth_line_id
    multi_line = multi_target.birth_line
    Notification.objects.create(
        recipient=admin_user,
        notification_type='approval',
        title='测试通知',
        content='测试采购单审批通知',
        related_object_type='transfer',
        related_object_id=single_doc.pk,
    )
    ApprovalCC.objects.create(
        transfer=single_doc,
        recipient=admin_user,
        approval_snapshot={'status': 'approved'},
    )

    preview = _run()
    assert '1 条审批抄送' in preview

    output = _run('--apply')

    assert '台账对账零差异' in output
    assert not FixedAsset.objects.filter(pk__in=[single_target.pk, multi_target.pk]).exists()
    assert not Transfer.objects.filter(pk=single_doc.pk).exists()
    assert not TransferLine.objects.filter(pk=single_line_id).exists()
    assert not Notification.objects.filter(related_object_id=single_doc.pk).exists()
    assert not ApprovalCC.objects.filter(transfer_id=single_doc.pk).exists()
    assert Transfer.objects.filter(pk=multi_doc.pk).exists()
    assert multi_doc.lines.count() == 7
    multi_line.refresh_from_db()
    assert multi_line.数量 == 41
    assert multi_line.金额 == Decimal('410.00')
    assert multi_line.instance_links.count() == 41
    assert AssetStock.objects.get(branch=yangzhou, item=item1).在库数量 == 0
    assert AssetStock.objects.get(branch=yangzhou, item=item2).在库数量 == 41
    assert InstanceSequence.objects.get(item=item1, branch=yangzhou).last_no == 1
    assert InstanceSequence.objects.get(item=item2, branch=yangzhou).last_no == 42
    assert not TransferLineInstance.objects.filter(instance__in=[single_target, multi_target]).exists()

    _purchase(
        yangzhou,
        'CG20261014-001',
        [(item1, 1, Decimal('100.00'), Decimal('100.00'))],
    )
    _purchase(
        yangzhou,
        'CG20261014-002',
        [(item2, 1, Decimal('10.00'), Decimal('10.00'))],
    )
    assert FixedAsset.objects.filter(
        item=item1, 内部编号='A-a00001-YZ001-1',
    ).exists()
    assert FixedAsset.objects.filter(
        item=item2, 内部编号='A-a00007-YZ001-42',
    ).exists()


@pytest.mark.django_db
def test_equal_link_counts_with_wrong_instance_abort(yangzhou):
    _single_doc, multi_doc, _item1, item2 = _create_targets(yangzhou)
    target_line = multi_doc.lines.get(item=item2)
    wrong_instance = FixedAsset.objects.filter(
        birth_line__transfer=multi_doc,
    ).exclude(item=item2).first()
    TransferLineInstance.objects.filter(instance=wrong_instance).delete()
    TransferLineInstance.objects.create(line=target_line, instance=wrong_instance)

    target_codes = ('A-a00001-YZ001-1', 'A-a00007-YZ001-42')
    target_ids = set(
        FixedAsset.objects.filter(内部编号__in=target_codes).values_list('pk', flat=True)
    )
    output = StringIO()
    with pytest.raises(CommandError, match='未执行任何修改'):
        call_command('prod_data_fix_yz_assets', '--apply', stdout=output)
    assert '出生实例与明细关联并非相同资产集合' in output.getvalue()

    assert set(
        FixedAsset.objects.filter(内部编号__in=target_codes).values_list('pk', flat=True)
    ) == target_ids


@pytest.mark.django_db
def test_manual_purchase_amount_blocks_deletion(yangzhou):
    single_doc, multi_doc, _item1, item2 = _create_targets(yangzhou)
    multi_line = multi_doc.lines.get(item=item2)
    multi_line.金额 = Decimal('421.00')
    multi_line.save(update_fields=['金额', 'updated_at'])
    target_ids = list(FixedAsset.objects.filter(branch=yangzhou).values_list('id', flat=True))

    with pytest.raises(CommandError, match='未执行任何修改'):
        _run('--apply')

    assert FixedAsset.objects.filter(id__in=target_ids).count() == 49
    assert Transfer.objects.filter(pk=single_doc.pk).exists()
    multi_line.refresh_from_db()
    assert multi_line.金额 == Decimal('421.00')
