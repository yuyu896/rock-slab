"""生产数据纠错命令测试：北京三分/五分电脑序列号清空。"""
import pytest
from django.core.management import call_command
from io import StringIO

from apps.assets.models import FixedAsset
from apps.categories.models import Category
from apps.organizations.models import Branch


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
    call_command('prod_data_fix_bj_serials', *args, stdout=out)
    return out.getvalue()


def _check_consistent():
    out = StringIO()
    call_command('check_ledger_consistency', stdout=out)
    return out.getvalue()


@pytest.fixture
def bj_branches(team):
    b3 = Branch.objects.create(name='北京三分', code='BJ003', team=team)
    b5 = Branch.objects.create(name='北京五分', code='BJ005', team=team)
    return b3, b5


def _inst(branch, item, no, serial):
    return FixedAsset.objects.create(
        item=item, 内部编号=no, 当前状态='在库', branch=branch, 序列号=serial,
    )


@pytest.mark.django_db
class TestBjSerialsClear:
    def test_clear_only_targets(self, bj_branches, second_branch):
        b3, b5 = bj_branches
        pc, phone = _item('A-a00011'), _item('BJS-P1')
        a = _inst(b3, pc, 'A-a00011-BJ003-1', 'A24734JKL3400492')
        b = _inst(b3, pc, 'A-a00011-BJ003-2', '')  # 已空
        c = _inst(b3, pc, 'A-a00011-BJ003-3', '自购')
        d = _inst(b5, pc, 'A-a00011-BJ005-1', 'A24734JBL4400047')
        keep_phone = _inst(b3, phone, 'BJS-P1-BJ003-1', 'SN-PHONE')      # 他品目
        keep_other = _inst(second_branch, pc, 'A-a00011-XB-1', 'SN-OTHER')  # 他分公司

        out = _run('--apply')
        assert '已写入：清空 3 条序列号' in out

        for i in (a, b, c, d):
            i.refresh_from_db()
            assert i.序列号 == ''
        keep_phone.refresh_from_db(); keep_other.refresh_from_db()
        assert keep_phone.序列号 == 'SN-PHONE'   # 他品目不动
        assert keep_other.序列号 == 'SN-OTHER'   # 他分公司不动
        assert not (a.序列号 or '').strip()      # 待补录判定口径（空=待补录）
        _check_consistent()

    def test_dry_run_and_idempotent(self, bj_branches):
        b3, _ = bj_branches
        _inst(b3, _item('A-a00011'), 'A-a00011-BJ003-9', 'X1')

        out = _run()
        assert 'dry-run' in out
        assert FixedAsset.objects.get(内部编号='A-a00011-BJ003-9').序列号 == 'X1'

        _run('--apply')
        assert FixedAsset.objects.get(内部编号='A-a00011-BJ003-9').序列号 == ''
        out = _run('--apply')
        assert '无需处理（幂等跳过）' in out
        _check_consistent()
