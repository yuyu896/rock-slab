"""单据分公司语义化执法（transfer-branch-semantics）：

业务代码禁止直接对 Transfer.from_branch / to_branch 赋值（含构造关键字参数）——
分公司装载唯一收口在 Transfer.build（模型内映射）。第 24 案「采购导入装反」的
结构性防线。
"""
import re
from pathlib import Path

import pytest

from apps.transfers.models import Transfer
from apps.organizations.models import Branch

# 白名单：模型自身（映射唯一所在）、迁移、测试
WHITELIST_PARTS = {'migrations', 'tests'}
WHITELIST_FILES = {'models.py'}

ASSIGN_RE = re.compile(r'\.(from_branch|to_branch)\s*=(?!=)')


@pytest.mark.django_db
class TestTransferBuild:
    def test_purchase_build_lands_to_branch(self, branch):
        t = Transfer.build(
            Transfer.ACTION_PURCHASE, {'单据编号': 'B-1', '调拨日期': '2026-09-14'},
            所属分公司=branch,
        )
        t.save()
        assert t.to_branch == branch and t.from_branch is None
        assert t.业务分公司 == branch
        assert t.业务分公司名 == t.调入分公司

    def test_assign_build_lands_from_branch(self, branch):
        t = Transfer.build(
            Transfer.ACTION_ASSIGN, {'单据编号': 'B-2', '调拨日期': '2026-09-14'},
            所属分公司=branch,
        )
        t.save()
        assert t.from_branch == branch and t.to_branch is None
        assert t.业务分公司 == branch

    def test_transfer_build_two_sides(self, branch, second_branch):
        t = Transfer.build(
            Transfer.ACTION_TRANSFER, {'单据编号': 'B-3', '调拨日期': '2026-09-14'},
            调出分公司=branch, 调入分公司=second_branch,
        )
        t.save()
        assert t.from_branch == branch and t.to_branch == second_branch
        assert t.业务分公司 == branch

    def test_illegal_param_combos_rejected(self, branch):
        with pytest.raises(ValueError):
            Transfer.build(Transfer.ACTION_PURCHASE, {}, 调出分公司=branch)
        with pytest.raises(ValueError):
            Transfer.build(Transfer.ACTION_TRANSFER, {}, 所属分公司=branch)
        with pytest.raises(ValueError):
            Transfer.build(Transfer.ACTION_ASSIGN, {}, 调入分公司=branch)


class TestNoDirectBranchAssignment:
    def test_business_code_no_from_to_assignment(self):
        apps_dir = Path(__file__).resolve().parent.parent / 'apps'
        violations = []
        for py in apps_dir.rglob('*.py'):
            rel = py.relative_to(apps_dir)
            if any(part in WHITELIST_PARTS for part in rel.parts) or rel.name in WHITELIST_FILES:
                continue
            try:
                text = py.read_text(encoding='utf-8')
            except UnicodeDecodeError:
                continue
            if 'Transfer' not in text and 'branch' not in text:
                continue
            for i, line in enumerate(text.splitlines(), 1):
                s = line.strip()
                if s.startswith('#'):
                    continue
                if ASSIGN_RE.search(s):
                    violations.append(f'{rel}:{i}: {s[:80]}')
        assert not violations, '分公司装载须走 Transfer.build（业务代码禁直赋 from/to）：\n' + '\n'.join(violations)
