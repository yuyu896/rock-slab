"""生产数据纠错回滚命令测试：泉州二分入库日期恢复出生快照。"""
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


def _item(code):
    item, _ = Category.objects.get_or_create(
        asset_code=code,
        defaults={
            'asset_category': '测试类目', 'item_category': '测试分类',
            'asset_name': f'品目 {code}', 'unit': '个',
            'management_type': 'instance',
        },
    )
    return item


def _run(*args):
    out = StringIO()
    call_command('prod_data_fix_qz2_revert', *args, stdout=out)
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
class TestQz2Revert:
    def test_revert_restores_snapshot(self, qz2):
        from unittest.mock import patch
        from apps.assets.management.commands.prod_data_fix_qz2_revert import TARGET_NUMBERS

        item = _item('QZR-I1')
        _purchase(qz2, item, 7, 'CG20250723-004', datetime.date(2025, 7, 23))
        insts = sorted(FixedAsset.objects.filter(branch=qz2), key=lambda x: x.内部编号)
        # 模拟前案误改：个体日期各不相同
        wrong = datetime.date(2025, 12, 5)
        for i in insts[:3]:
            i.入库日期 = wrong
            i.save(update_fields=['入库日期'])

        with patch('apps.assets.management.commands.prod_data_fix_qz2_revert.TARGET_NUMBERS',
                   tuple(i.内部编号 for i in insts)):
            out = _run('--apply')

        assert '已写入：回滚 3 条入库日期' in out
        assert all(
            i.入库日期 == datetime.date(2025, 7, 23)
            for i in FixedAsset.objects.filter(branch=qz2)
        )  # 全部恢复出生单日期

    def test_missing_and_idempotent(self, qz2):
        from unittest.mock import patch
        from apps.assets.management.commands.prod_data_fix_qz2_revert import TARGET_NUMBERS
        item = _item('QZR-I2')
        _purchase(qz2, item, 2, 'CG20250707-014', datetime.date(2025, 7, 7))
        real = FixedAsset.objects.filter(branch=qz2).first().内部编号

        with patch('apps.assets.management.commands.prod_data_fix_qz2_revert.TARGET_NUMBERS',
                   (real, 'A-a00007-QZ002-99')):
            with pytest.raises(CommandError, match='缺失'):
                _run('--apply')  # 部分缺失即中止

        with patch('apps.assets.management.commands.prod_data_fix_qz2_revert.TARGET_NUMBERS',
                   (real,)):
            out = _run('--apply')
            assert '已写入：回滚 0 条' in out  # 出生即快照，幂等
