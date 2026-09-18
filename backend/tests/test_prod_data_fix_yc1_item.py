"""生产数据纠错命令测试：盐城品目整体更正（A-a00008→A-a00011 含换号）。"""
import datetime
import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from io import StringIO

from apps.assets.models import AssetStock, FixedAsset, InstanceSequence
from apps.assets.services import ledger
from apps.categories.models import Category
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
    return item


def _run(*args):
    out = StringIO()
    call_command('prod_data_fix_yc1_item', *args, stdout=out)
    return out.getvalue()


def _check_consistent():
    out = StringIO()
    call_command('check_ledger_consistency', stdout=out)
    return out.getvalue()


@pytest.fixture
def yc(team):
    return Branch.objects.create(name='盐城分公司', code='YC001', team=team)


def _birth_doc(branch, item, qty, no):
    """纯单采购：单行 ×qty，出生 qty 个实例。"""
    t = Transfer.build(
        'purchase',
        {'调拨日期': datetime.date(2026, 9, 11), '审批状态': '已入库', '单据编号': no,
         '调入分公司': branch.name, '创建人': '测试'},
        所属分公司=branch,
    )
    t.save()
    TransferLine.objects.create(transfer=t, item=item, 行号=1, 数量=qty)
    ledger.apply_document(t)
    return Transfer.objects.get(pk=t.pk)


@pytest.mark.django_db
class TestYc1ItemCorrection:
    def test_full_correction_four_way_sync(self, yc, second_branch):
        old_item, new_item = _item('A-a00008'), _item('A-a00011')
        d = _birth_doc(yc, old_item, 3, 'CG20260911-016')
        # 他分公司同品目基准
        _birth_doc(second_branch, old_item, 2, 'CG20260911-099')
        # 造一条序列号验证保留
        FixedAsset.objects.filter(branch=yc).update(序列号='SN-KEEP-1')

        out = _run('--apply')
        assert '已写入：3 实例品目+编号更正' in out

        assert FixedAsset.objects.filter(branch=yc, item=old_item).count() == 0
        news = list(FixedAsset.objects.filter(branch=yc, item=new_item).order_by('内部编号'))
        assert [i.内部编号 for i in news] == ['A-a00011-YC001-1', 'A-a00011-YC001-2', 'A-a00011-YC001-3']
        assert all(i.序列号 == 'SN-KEEP-1' for i in news)  # 序列号保留
        ln = d.lines.first(); ln.refresh_from_db()
        assert ln.item_id == new_item.id  # 出生行更正
        assert AssetStock.objects.filter(branch=yc, item=old_item).count() == 0  # 旧行删
        r = AssetStock.objects.get(branch=yc, item=new_item)
        assert r.在库数量 == 3
        seq = InstanceSequence.objects.get(item=new_item, branch=yc)
        assert seq.last_no == 3
        # 他司零波及
        assert FixedAsset.objects.filter(branch=second_branch, item=old_item).count() == 2
        assert AssetStock.objects.get(branch=second_branch, item=old_item).在库数量 == 2
        _check_consistent()

    def test_lifecycle_link_rejects(self, yc):
        old_item, _new_item = _item('A-a00008'), _item('A-a00011')
        d = _birth_doc(yc, old_item, 2, 'CG20260911-020')
        inst = FixedAsset.objects.filter(branch=yc).first()
        a = Transfer.build(
            'assign',
            {'调拨日期': datetime.date(2026, 9, 12), '审批状态': '已通过',
             '单据编号': 'LY20260912-001', '调出分公司': yc.name},
            所属分公司=yc,
        )
        a.save()
        line = TransferLine.objects.create(transfer=a, item=old_item, 行号=1, 数量=1)
        TransferLineInstance.objects.create(line=line, instance=inst)
        ledger.apply_document(a)

        with pytest.raises(CommandError, match='生平'):
            _run('--apply')
        assert FixedAsset.objects.filter(branch=yc, item=old_item).count() == 2  # 零变更

    def test_new_number_occupied_rejects(self, yc, second_branch):
        old_item, new_item = _item('A-a00008'), _item('A-a00011')
        _birth_doc(yc, old_item, 2, 'CG20260911-021')
        # 他分公司占用目标编号 A-a00011-YC001-1（全局唯一约束域）
        FixedAsset.objects.create(
            item=new_item, 内部编号='A-a00011-YC001-1', 当前状态='在库', branch=second_branch,
        )

        with pytest.raises(CommandError, match='已被占用'):
            _run('--apply')

    def test_dry_run_and_idempotent(self, yc):
        _item('A-a00011')
        _birth_doc(yc, _item('A-a00008'), 2, 'CG20260911-022')

        out = _run()
        assert 'dry-run' in out
        assert FixedAsset.objects.filter(branch=yc, item__asset_code='A-a00008').count() == 2

        _run('--apply')
        out = _run('--apply')
        assert '无需处理（幂等跳过）' in out
        _check_consistent()
