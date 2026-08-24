"""存量迁移（期初单）与机器执法（对账/架构测试）契约测试。

对应 initial-ledger-migration / ledger-consistency-guard 能力。
"""
import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from io import StringIO

from apps.assets.models import AssetStock, LedgerAdjustment
from apps.assets.services import ledger


def _item(code):
    from apps.categories.models import Category
    item, _ = Category.objects.get_or_create(
        asset_code=code,
        defaults={'asset_category': 't', 'item_category': 't', 'asset_name': code, 'unit': '个'},
    )
    return item


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
        """期初单吸收历史后，其后的单据参与重算（期初经增量导入语义的调整单入账）。"""
        from apps.transfers.models import Transfer, TransferLine
        item = _item('CK-003')
        # 历史（期初前）单据：被期初吸收，不参与重算
        transfer = Transfer.objects.create(
            调拨日期='2026-01-01',
            调出分公司=branch.name, from_branch=branch,
            action_type='purchase', 审批状态='已入库',
        )
        TransferLine.objects.create(transfer=transfer, item=item, 行号=1, 数量=99)
        # 期初入账：is_initial 调整单（P2 第三刀起唯一期初形态）
        ledger.apply_adjustment(branch, item, ledger.COLUMN_STOCK, 6, '系统期初', is_initial=True)
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
        from apps.transfers.models import Transfer, TransferLine
        from datetime import date
        item = _item('CK-003')
        transfer = Transfer.objects.create(
            调拨日期=date(2026, 1, 1),
            调出分公司=branch.name, from_branch=branch,
            action_type='purchase', 审批状态='已入库',
        )
        TransferLine.objects.create(transfer=transfer, item=item, 行号=1, 数量=5)
        code, text = _check()
        assert code == 0
        assert '未初始化' in text
        assert '台账增量导入' in text

    def test_any_ledger_row_enforces_strict(self, branch):
        """只要台账有行（哪怕无期初单），即严格对账。"""
        from apps.transfers.models import Transfer, TransferLine
        item = _item('CK-009')
        ledger.apply_adjustment(branch, item, ledger.COLUMN_STOCK, 3, '造数')
        transfer = Transfer.objects.create(
            调拨日期='2026-01-01',
            调出分公司=branch.name, from_branch=branch,
            action_type='purchase', 审批状态='已入库',
        )
        TransferLine.objects.create(transfer=transfer, item=item, 行号=1, 数量=5)
        code, _ = _check()
        assert code == 1  # 调整单 3 + 采购 5 = 8 ≠ 台账 3
