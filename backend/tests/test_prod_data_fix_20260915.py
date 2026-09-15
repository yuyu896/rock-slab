"""生产数据纠错两案命令测试：台州工作手机品目清删 / 苏州实例整清。"""
import datetime
import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from io import StringIO

from apps.assets.models import AssetStock, FixedAsset
from apps.assets.services import ledger
from apps.categories.models import Category
from apps.notifications.models import Notification
from apps.organizations.models import Branch
from apps.transfers.models import Transfer, TransferLine


# ---------------------------------------------------------------------------
# helpers（与 0914 测试同模式）
# ---------------------------------------------------------------------------

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


def _purchase(branch, item, qty, no, extra_lines=()):
    """生效采购单：extra_lines 为追加的 (item, qty) 行（造混行单用）。"""
    t = Transfer.build(
        'purchase',
        {'调拨日期': datetime.date(2025, 4, 13), '审批状态': '已入库', '单据编号': no,
         '调入分公司': branch.name, '创建人': '测试'},
        所属分公司=branch,
    )
    t.save()
    TransferLine.objects.create(transfer=t, item=item, 行号=1, 数量=qty)
    for i, (li, lq) in enumerate(extra_lines, start=2):
        TransferLine.objects.create(transfer=t, item=li, 行号=i, 数量=lq)
    ledger.apply_document(t)
    return Transfer.objects.get(pk=t.pk)


def _run(*args):
    out = StringIO()
    call_command('prod_data_fix_20260915', *args, stdout=out)
    return out.getvalue()


def _check_consistent():
    out = StringIO()
    call_command('check_ledger_consistency', stdout=out)  # 差异即 SystemExit
    return out.getvalue()


@pytest.fixture
def taizhou(team):
    return Branch.objects.create(name='19分台州', code='TZ019', team=team)


@pytest.fixture
def suzhou(team):
    return Branch.objects.create(name='20分苏州', code='SZ020', team=team)


# ---------------------------------------------------------------------------
# 案A 台州 × 工作手机（品目维度）
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestTaizhouPhoneWipe:
    def test_item_scoped_wipe_other_branches_untouched(self, taizhou, second_branch):
        phone = _item('A-a00007')
        other_inst = _item('TZB-I1')
        qty_item = _item('TZB-Q1', 'quantity')
        d1 = _purchase(taizhou, phone, 2, 'CG20250901-001')
        d2 = _purchase(taizhou, phone, 3, 'CG20250901-002')
        keep_inst = _purchase(taizhou, other_inst, 1, 'CG20250901-003')
        keep_qty = _purchase(taizhou, qty_item, 7, 'CG20250901-004')
        # 他分公司同品目数据：必须零波及
        other_doc = _purchase(second_branch, phone, 4, 'CG20250901-101')

        out = _run('--apply')
        assert '已写入：删 2 单 / 5 实例' in out

        assert FixedAsset.objects.filter(branch=taizhou, item=phone).count() == 0
        assert not Transfer.objects.filter(pk__in=[d1.pk, d2.pk]).exists()
        assert AssetStock.objects.get(branch=taizhou, item=phone).在库数量 == 0
        # 本分公司他品目不动
        assert Transfer.objects.filter(pk=keep_inst.pk).exists()
        assert FixedAsset.objects.filter(branch=taizhou, item=other_inst).count() == 1
        assert AssetStock.objects.get(branch=taizhou, item=qty_item).在库数量 == 7
        assert Transfer.objects.filter(pk=keep_qty.pk).exists()
        # 他分公司同品目零波及
        assert Transfer.objects.filter(pk=other_doc.pk).exists()
        assert AssetStock.objects.get(branch=second_branch, item=phone).在库数量 == 4
        assert FixedAsset.objects.filter(branch=second_branch, item=phone).count() == 4
        _check_consistent()

    def test_mixed_birth_doc_rejected_untouched(self, taizhou):
        phone = _item('A-a00007')
        extra = _item('TZB-I2')
        doc = _purchase(taizhou, phone, 2, 'CG20250901-020', extra_lines=[(extra, 1)])

        with pytest.raises(CommandError, match='混行单'):
            _run('--apply')

        assert Transfer.objects.filter(pk=doc.pk).exists()  # 零变更
        assert FixedAsset.objects.filter(branch=taizhou, item=phone).count() == 2

    def test_mirror_mismatch_rejected(self, taizhou):
        phone = _item('A-a00007')
        _purchase(taizhou, phone, 2, 'CG20250901-030')
        row = AssetStock.objects.get(branch=taizhou, item=phone)
        row.在库数量 = 9  # 直改破坏镜像（tests 在架构白名单内）
        row.save(update_fields=['在库数量'])

        with pytest.raises(CommandError, match='镜像不一致'):
            _run('--apply')
        assert FixedAsset.objects.filter(branch=taizhou, item=phone).count() == 2


# ---------------------------------------------------------------------------
# 案B 苏州实例整清（分公司维度）
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestSuzhouWipe:
    def test_branch_wipe_keep_quantity_stock(self, suzhou):
        p1, p2 = _item('SZB-I1'), _item('SZB-I2')
        qty_item = _item('SZB-Q1', 'quantity')
        d1 = _purchase(suzhou, p1, 3, 'CG20250901-201')
        d2 = _purchase(suzhou, p2, 2, 'CG20250901-202')
        dq = _purchase(suzhou, qty_item, 6, 'CG20250901-203')

        out = _run('--apply')
        assert '已写入：删 2 单 / 5 实例' in out

        assert FixedAsset.objects.filter(branch=suzhou).count() == 0
        assert not Transfer.objects.filter(pk__in=[d1.pk, d2.pk]).exists()
        assert Transfer.objects.filter(pk=dq.pk).exists()
        assert AssetStock.objects.get(branch=suzhou, item=p1).在库数量 == 0
        assert AssetStock.objects.get(branch=suzhou, item=p2).在库数量 == 0
        assert AssetStock.objects.get(branch=suzhou, item=qty_item).在库数量 == 6
        _check_consistent()

    def test_reimport_numbering_continues(self, suzhou):
        p1 = _item('SZB-I3')
        _purchase(suzhou, p1, 2, 'CG20250901-210')
        old = set(
            FixedAsset.objects.filter(branch=suzhou, item=p1).values_list('内部编号', flat=True)
        )
        _run('--apply')
        _purchase(suzhou, p1, 2, 'CG20250901-211')
        new = set(
            FixedAsset.objects.filter(branch=suzhou, item=p1).values_list('内部编号', flat=True)
        )
        assert len(new) == 2 and not (new & old)
        assert all(n > max(old) for n in new)
        _check_consistent()


# ---------------------------------------------------------------------------
# 安全形态：dry-run / 幂等
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestSafetyShape:
    def test_dry_run_writes_nothing(self, taizhou, suzhou):
        phone = _item('A-a00007')
        d1 = _purchase(taizhou, phone, 2, 'CG20250901-301')
        d2 = _purchase(suzhou, _item('DRZ-I1'), 1, 'CG20250901-302')

        out = _run()

        assert 'dry-run' in out
        assert FixedAsset.objects.filter(branch=taizhou).count() == 2
        assert FixedAsset.objects.filter(branch=suzhou).count() == 1
        assert Transfer.objects.filter(pk__in=[d1.pk, d2.pk]).count() == 2

    def test_idempotent_rerun(self, taizhou, suzhou):
        _purchase(taizhou, _item('A-a00007'), 1, 'CG20250901-401')
        _purchase(suzhou, _item('IDZ-I1'), 1, 'CG20250901-402')

        _run('--apply')
        out = _run('--apply')

        assert '该分公司该品目无实例，无需处理' in out
        assert '无实例档案，无需处理' in out
        assert '对账复验' in out
        _check_consistent()
