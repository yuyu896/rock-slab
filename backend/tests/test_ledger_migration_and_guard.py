"""存量迁移（期初单）与机器执法（对账/架构测试）契约测试。

对应 initial-ledger-migration / ledger-consistency-guard 能力。
"""
import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from io import StringIO

from apps.assets.models import Asset, AssetStock, LedgerAdjustment
from apps.assets.services import ledger
from apps.organizations.models import Department


def _item(code):
    from apps.categories.models import Category
    item, _ = Category.objects.get_or_create(
        asset_code=code,
        defaults={'asset_category': 't', 'item_category': 't', 'asset_name': code, 'unit': '个'},
    )
    return item


def _make_asset(branch, code, qty, status='在库', dept=''):
    return Asset.objects.create(
        序号=_next_seq(), 分公司=branch.name, 分公司编号=branch.code, branch=branch,
        资产编号=code, 资产类目='t', 物品分类='t', 资产名称=code,
        数量=qty, 当前状态=status, 所属部门=dept,
    )


def _next_seq():
    last = Asset.objects.order_by('-序号').first()
    return (last.序号 + 1) if last else 1


def _check():
    out = StringIO()
    try:
        call_command('check_ledger_consistency', stdout=out)
        return 0, out.getvalue()
    except SystemExit as e:
        return e.code, out.getvalue()


# ---------------------------------------------------------------------------
# 分桶与期初单
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestInitialMigration:
    def test_status_bucketing_rules(self, branch):
        _item('MG-001')
        _make_asset(branch, 'MG-001', 5, status='在库')
        _make_asset(branch, 'MG-001', 2, status='使用中')
        _make_asset(branch, 'MG-001', 1, status='维修中')
        _make_asset(branch, 'MG-001', 3, status='报废')  # 出局不计

        out = StringIO()
        call_command('migrate_initial_ledger', '--confirm-backup', stdout=out)

        row = AssetStock.objects.get(branch=branch, item__asset_code='MG-001')
        assert row.在库数量 == 5
        assert row.在用数量 == 3  # 使用中 2 + 维修中 1
        code, _ = _check()
        assert code == 0  # 期初单生成后立即对账零差异

    def test_initial_adjustments_created(self, branch):
        _item('MG-002')
        _make_asset(branch, 'MG-002', 4, status='在库', dept='行政部')
        out = StringIO()
        call_command('migrate_initial_ledger', '--confirm-backup', stdout=out)
        adj = LedgerAdjustment.objects.get(item__asset_code='MG-002', is_initial=True)
        assert adj.变动量 == 4 and adj.事由 == '系统期初'

    def test_unregistered_code_blocks_migration(self, branch):
        _item('MG-003')
        _make_asset(branch, 'MG-UNKNOWN-1', 2)  # 未登记
        with pytest.raises(CommandError, match='未登记'):
            call_command('migrate_initial_ledger', '--confirm-backup')
        assert not AssetStock.objects.exists()

    def test_requires_backup_confirmation(self, branch):
        with pytest.raises(CommandError, match='备份'):
            call_command('migrate_initial_ledger')

    def test_department_normalization(self, branch):
        _item('MG-004')
        _make_asset(branch, 'MG-004', 1, dept='行政部')
        _make_asset(branch, 'MG-004', 1, dept='行政部')  # 重复文本归一
        _make_asset(branch, 'MG-004', 1, dept='仓库')
        out = StringIO()
        call_command('migrate_initial_ledger', '--confirm-backup', stdout=out)
        depts = set(Department.objects.filter(branch=branch).values_list('name', flat=True))
        assert depts == {'行政部', '仓库'}

    def test_rerun_requires_reset(self, branch):
        _item('MG-005')
        _make_asset(branch, 'MG-005', 1)
        call_command('migrate_initial_ledger', '--confirm-backup')
        with pytest.raises(CommandError, match='reset'):
            call_command('migrate_initial_ledger', '--confirm-backup')

    def test_preview_reports_unregistered_with_suggestion(self, branch):
        _item('MG-006')
        _make_asset(branch, 'MG-006X', 1)
        out = StringIO()
        call_command('preview_ledger_migration', stdout=out)
        text = out.getvalue()
        assert 'MG-006X' in text
        assert '阻断' in text


# ---------------------------------------------------------------------------
# 对账命令
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestCheckLedgerConsistency:
    def test_zero_diff_after_documents(self, branch):
        item = _item('CK-001')
        ledger.apply_adjustment(branch, item, ledger.COLUMN_STOCK, 10, '造数')
        code, text = _check()
        assert code == 0

    def test_drift_detected(self, branch):
        item = _item('CK-002')
        ledger.apply_adjustment(branch, item, ledger.COLUMN_STOCK, 10, '造数')
        row = AssetStock.objects.get(branch=branch, item=item)
        row.在库数量 = 8  # 绕过唯一写入口的漂移
        row.save(update_fields=['在库数量'])
        code, text = _check()
        assert code == 1
        assert 'CK-002' in text

    def test_post_initial_documents_reconcile(self, branch):
        """期初单吸收历史后，其后的单据参与重算。"""
        from apps.transfers.models import Transfer
        from django.utils import timezone
        _item('CK-003')
        # 历史（期初前）单据：不参与重算
        Transfer.objects.create(
            调拨日期='2026-01-01', 资产编号='CK-003', 资产名称='x', 调拨数量=99,
            调出分公司=branch.name, from_branch=branch,
            action_type='purchase', 审批状态='已入库',
        )
        _make_asset(branch, 'CK-003', 6)
        call_command('migrate_initial_ledger', '--confirm-backup')
        row = AssetStock.objects.get(branch=branch, item__asset_code='CK-003')
        assert row.在库数量 == 6  # 历史单据被期初吸收，不重复计
        code, _ = _check()
        assert code == 0


# ---------------------------------------------------------------------------
# 架构测试：唯一写入口
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestLedgerArchitecture:
    def test_ledger_write_patterns_confined_to_service(self):
        """台账数量写操作仅允许出现在 services/ledger.py、migrations、tests。"""
        from pathlib import Path
        backend_apps = Path(__file__).resolve().parent.parent / 'apps'

        write_patterns = (
            '在库数量', '在用数量', '回收库数量',
        )
        allowed_files = {'ledger.py', 'models.py', 'serializers.py'}
        allowed_dirs = {'migrations', 'services', 'tests'}

        violations = []
        for py in backend_apps.rglob('*.py'):
            rel = py.relative_to(backend_apps)
            if any(part in allowed_dirs for part in rel.parts[:-1]):
                continue
            if rel.name in allowed_files:
                continue
            try:
                text = py.read_text(encoding='utf-8')
            except UnicodeDecodeError:
                continue
            for i, line in enumerate(text.splitlines(), 1):
                s = line.strip()
                if s.startswith('#') or s.startswith('"""') or s.startswith("'''"):
                    continue
                # 写模式：对这些列的赋值 / F() 表达式 / update(
                for col in write_patterns:
                    if col in s and (
                        s.startswith(col) and '=' in s and '==' not in s.split('=')[0] + '='
                        or f"F('{col}')" in s or f'F("{col}")' in s
                    ):
                        violations.append(f'{rel}:{i}: {s[:80]}')

        assert not violations, '台账写操作越权（铁律 2）：\n' + '\n'.join(violations)

    def test_no_direct_stock_update_outside_service(self):
        """视图层不得出现 AssetStock 的 .update(/F( 直改。"""
        from pathlib import Path
        backend_apps = Path(__file__).resolve().parent.parent / 'apps'
        violations = []
        for py in backend_apps.rglob('*.py'):
            rel = py.relative_to(backend_apps)
            if 'migrations' in rel.parts or 'services' in rel.parts:
                continue
            try:
                text = py.read_text(encoding='utf-8')
            except UnicodeDecodeError:
                continue
            for i, line in enumerate(text.splitlines(), 1):
                s = line.strip()
                if 'AssetStock' in s and ('.update(' in s or '.bulk_update(' in s):
                    violations.append(f'{rel}:{i}: {s[:80]}')
        assert not violations, '视图层直接批量改台账：\n' + '\n'.join(violations)


@pytest.mark.django_db
class TestUninitializedTolerance:
    def test_empty_ledger_without_initial_passes_with_warning(self, branch):
        """未初始化（无期初单+台账空+有历史单据）：通过并提示，供 deploy.sh 中间态放行。"""
        from apps.transfers.models import Transfer
        from datetime import date
        Transfer.objects.create(
            调拨日期=date(2026, 1, 1), 资产编号='CK-003', 资产名称='x', 调拨数量=5,
            调出分公司=branch.name, from_branch=branch,
            action_type='purchase', 审批状态='已入库',
        )
        code, text = _check()
        assert code == 0
        assert '未初始化' in text

    def test_any_ledger_row_enforces_strict(self, branch):
        """只要台账有行（哪怕无期初单），即严格对账。"""
        from apps.transfers.models import Transfer
        item = _item('CK-009')
        ledger.apply_adjustment(branch, item, ledger.COLUMN_STOCK, 3, '造数')
        Transfer.objects.create(
            调拨日期='2026-01-01', 资产编号='CK-009', 资产名称='x', 调拨数量=5,
            调出分公司=branch.name, from_branch=branch,
            action_type='purchase', 审批状态='已入库',
        )
        code, _ = _check()
        assert code == 1  # 调整单 3 + 采购 5 = 8 ≠ 台账 3
