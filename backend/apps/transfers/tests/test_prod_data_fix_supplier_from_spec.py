"""prod_data_fix_supplier_from_spec：规格错填供应商归位——圈定/保护/dry-run/幂等。"""
import pytest
from django.core.management import call_command

from apps.categories.models import Category
from apps.organizations.models import Branch, Region, Team
from apps.transfers.models import Transfer, TransferLine

pytestmark = pytest.mark.django_db


def _branch():
    branch = Branch.objects.filter(name='规格纠错测试分公司').first()
    if branch:
        return branch
    region = Region.objects.create(name='规格纠错测试区域', code='SPECT', status='active')
    team = Team.objects.create(name='规格纠错测试组', region=region, status='active')
    return Branch.objects.create(name='规格纠错测试分公司', code='SPECT1', team=team, address='', phone='')


def _mk_line(name, spec, supplier='', header_supplier=''):
    branch = _branch()
    item = Category.objects.create(
        asset_category='IT', item_category='x', asset_name=name,
        asset_code=f'SPEC-{TransferLine.objects.count() + 1}',
        unit='台', management_type='instance',
    )
    head = Transfer.objects.create(
        单据编号=f'SPEC{Transfer.objects.count() + 1}', 调拨日期=__import__('datetime').date.today(),
        调入分公司=branch.name, to_branch=branch, action_type='purchase', 供应商=header_supplier,
    )
    return TransferLine.objects.create(
        transfer=head, item=item, 行号=1, 数量=1, 本批规格=spec, 供应商=supplier,
    )


def test_computer_exact_and_phone_contains_hit():
    computer = _mk_line('笔记本电脑', '小熊U租')
    zvgou = _mk_line('台式电脑', '自购')
    phone = _mk_line('测试手机', '华为 Mate60')
    _mk_line('打印机', '小熊')          # 跨类不命中
    _mk_line('台式电脑', '戴尔 7010')   # 电脑但规格不在名单
    call_command('prod_data_fix_supplier_from_spec', '--apply')
    computer.refresh_from_db()
    zvgou.refresh_from_db()
    phone.refresh_from_db()
    assert computer.供应商 == '小熊U租' and computer.本批规格 == ''
    assert zvgou.供应商 == '自购' and zvgou.本批规格 == ''
    assert phone.供应商 == '华为 Mate60' and phone.本批规格 == ''


def test_existing_supplier_kept_spec_cleared():
    line = _mk_line('笔记本电脑', '悟空', supplier='既有供应商')
    header_only = _mk_line('办公手机', '自购', header_supplier='单头供应商')
    call_command('prod_data_fix_supplier_from_spec', '--apply')
    line.refresh_from_db()
    header_only.refresh_from_db()
    # 命中行规格一律清空；既有供应商沿用不覆盖（行级或单头）
    assert line.供应商 == '既有供应商' and line.本批规格 == ''
    assert header_only.本批规格 == ''


def test_dry_run_no_write():
    line = _mk_line('笔记本电脑', '易点云')
    call_command('prod_data_fix_supplier_from_spec')
    line.refresh_from_db()
    assert line.本批规格 == '易点云' and line.供应商 == ''


def test_idempotent():
    line = _mk_line('笔记本电脑', '小熊')
    call_command('prod_data_fix_supplier_from_spec', '--apply')
    call_command('prod_data_fix_supplier_from_spec', '--apply')
    line.refresh_from_db()
    assert line.供应商 == '小熊' and line.本批规格 == ''
