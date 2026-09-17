"""生产数据纠错命令测试：泉州二分按内部编号修正入库日期（记录性字段）。"""
import datetime
import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from io import StringIO

from apps.assets.models import FixedAsset
from apps.assets.services import ledger
from apps.categories.models import Category
from apps.organizations.models import Branch
from apps.transfers.models import Transfer, TransferLine


def _item(code, management_type='instance'):
    item, _ = Category.objects.get_or_create(
        asset_code=code,
        defaults={
            'asset_category': '测试类目', 'item_category': '测试分类',
            'asset_name': f'品目 {code}', 'unit': '个',
            'management_type': management_type,
        },
    )
    return item


def _run(*args):
    out = StringIO()
    call_command('prod_data_fix_qz2_dates', *args, stdout=out)
    return out.getvalue()


def _check_consistent():
    out = StringIO()
    call_command('check_ledger_consistency', stdout=out)
    return out.getvalue()


@pytest.fixture
def qz2(team):
    return Branch.objects.create(name='泉州二分', code='QZ002', team=team)


def _purchase(branch, item, qty, no, date):
    t = Transfer.build(
        'purchase',
        {'调拨日期': date, '审批状态': '已入库', '单据编号': no,
         '调入分公司': branch.name, '创建人': '测试'},
        所属分公司=branch,
    )
    t.save()
    TransferLine.objects.create(transfer=t, item=item, 行号=1, 数量=qty)
    ledger.apply_document(t)
    return Transfer.objects.get(pk=t.pk)


@pytest.mark.django_db
class TestQz2DateFix:
    def test_dates_updated_docs_untouched(self, qz2, second_branch):
        from unittest.mock import patch
        from apps.assets.management.commands.prod_data_fix_qz2_dates import TARGET_DATES

        item = _item('QZD-I1')
        d1 = _purchase(qz2, item, 4, 'CG20250723-004', datetime.date(2025, 7, 23))
        d2 = _purchase(qz2, item, 3, 'CG20250707-014', datetime.date(2025, 7, 7))
        other = _purchase(second_branch, item, 2, 'CG20250707-099', datetime.date(2025, 7, 7))
        insts = sorted(FixedAsset.objects.filter(branch=qz2).values_list('内部编号', flat=True))

        targets = {
            insts[0]: datetime.date(2025, 7, 25),
            insts[1]: datetime.date(2025, 12, 5),
            insts[4]: datetime.date(2025, 7, 7),   # d2 出生，现值相同 → 幂等空改
            insts[3]: datetime.date(2025, 1, 6),
        }
        with patch('apps.assets.management.commands.prod_data_fix_qz2_dates.TARGET_DATES', targets):
            out = _run('--apply')

        assert '已写入：更新 3 条入库日期' in out
        for no, expect in targets.items():
            assert FixedAsset.objects.get(内部编号=no).入库日期 == expect
        # 未列入目标的实例不动
        for no in insts[4:]:
            assert FixedAsset.objects.get(内部编号=no).入库日期 in (
                datetime.date(2025, 7, 23), datetime.date(2025, 7, 7),
            )
        # 出生单据日期不动 + 他分公司不动
        d1.refresh_from_db(); d2.refresh_from_db(); other.refresh_from_db()
        assert d1.调拨日期 == datetime.date(2025, 7, 23)
        assert d2.调拨日期 == datetime.date(2025, 7, 7)
        assert all(
            i.入库日期 == datetime.date(2025, 7, 7)
            for i in FixedAsset.objects.filter(branch=second_branch)
        )
        _check_consistent()

    def test_partial_missing_target_aborts(self, qz2):
        from unittest.mock import patch
        from apps.assets.management.commands.prod_data_fix_qz2_dates import TARGET_DATES

        _purchase(qz2, _item('QZD-I2'), 2, 'CG20250723-005', datetime.date(2025, 7, 23))
        real = FixedAsset.objects.filter(branch=qz2).first().内部编号
        with patch('apps.assets.management.commands.prod_data_fix_qz2_dates.TARGET_DATES',
                   {real: datetime.date(2025, 8, 1), 'A-a00007-QZ002-99': datetime.date(2025, 8, 1)}):
            with pytest.raises(CommandError, match='缺失'):
                _run('--apply')
        assert FixedAsset.objects.get(内部编号=real).入库日期 == datetime.date(2025, 7, 23)  # 零变更

    def test_dry_run_and_idempotent(self, qz2):
        from unittest.mock import patch
        from apps.assets.management.commands.prod_data_fix_qz2_dates import TARGET_DATES

        item = _item('QZD-I3')
        _purchase(qz2, item, 2, 'CG20250723-006', datetime.date(2025, 7, 23))
        insts = sorted(FixedAsset.objects.filter(branch=qz2).values_list('内部编号', flat=True))
        targets = {insts[0]: datetime.date(2025, 5, 7)}

        with patch('apps.assets.management.commands.prod_data_fix_qz2_dates.TARGET_DATES', targets):
            out = _run()
            assert 'dry-run' in out
            assert FixedAsset.objects.get(内部编号=insts[0]).入库日期 == datetime.date(2025, 7, 23)

            _run('--apply')
            assert FixedAsset.objects.get(内部编号=insts[0]).入库日期 == datetime.date(2025, 5, 7)
            out = _run('--apply')
            assert '实际更新 0 条' in out
        _check_consistent()
