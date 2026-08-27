"""P2 第二刀：单据 × 实例绑定契约——输入矩阵、五单实例迁移、实例不变量与架构执法。

对应 document-instance-binding / fixed-asset-instance / ledger-consistency-guard 能力。
"""
import re
from io import StringIO
from pathlib import Path

import pytest
from rest_framework import status

from apps.assets.models import AssetStock, FixedAsset, InstanceSequence
from apps.assets.services import ledger


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _item(code, management_type='instance'):
    from apps.categories.models import Category
    item, _ = Category.objects.get_or_create(
        asset_code=code,
        defaults={
            'asset_category': '测试类目', 'item_category': '测试分类',
            'asset_name': f'品目 {code}', 'unit': '个',
            'management_type': management_type,
        },
    )
    return item


def _seed(branch, item, stock=0, in_use=0, recycle=0):
    """经调整单（唯一写入口）造台账底数，与实例计数保持镜像一致。"""
    if stock:
        ledger.apply_adjustment(branch, item, ledger.COLUMN_STOCK, stock, '测试造数')
    if in_use:
        ledger.apply_adjustment(branch, item, ledger.COLUMN_IN_USE, in_use, '测试造数')
    if recycle:
        ledger.apply_adjustment(branch, item, ledger.COLUMN_RECYCLE, recycle, '测试造数')
    return AssetStock.objects.get(branch=branch, item=item)


def _make_instances(branch, item, state, n, start=0, user=''):
    """直造实例（tests 在架构白名单内）；台账底数用 _seed 对齐。"""
    seq = InstanceSequence.objects.filter(item=item).first()
    base = seq.last_no if seq else start
    made = []
    for i in range(n):
        made.append(FixedAsset.objects.create(
            item=item, 内部编号=f'{item.asset_code}-{base + i + 1}',
            当前状态=state, branch=branch, 使用人=user,
        ))
    InstanceSequence.objects.update_or_create(
        item=item, defaults={'last_no': base + n},
    )
    return made


def _line(item, instances, **extra):
    line = {'item': str(item.id), '数量': len(instances),
            'instances': [str(i.id) for i in instances]}
    line.update(extra)
    return line


def _dept(branch):
    """领用行必填的部门外键（分公司 × 部门名字典）。"""
    from apps.organizations.models import Department
    dept, _ = Department.objects.get_or_create(branch=branch, name='测试部门')
    return dept


def _approve(client, tid):
    return client.post(f'/api/transfers/{tid}/approve', {'approved': True}, format='json')


# ---------------------------------------------------------------------------
# 输入矩阵（创建/编辑预检）
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestInstanceInputMatrix:
    def _assign(self, client, branch, item, line):
        """领用单公共入口：行默认带部门（使用人留给专门的失败用例省略）。"""
        line = {**{'department': str(_dept(branch).id)}, **line}
        return client.post('/api/transfers/assign', {
            '调拨日期': '2026-08-23', '调出分公司': branch.name, 'items': [line],
        }, format='json')

    def test_assign_requires_instances(self, authenticated_client, branch):
        item = _item('IB-001')
        _seed(branch, item, stock=2)
        _make_instances(branch, item, '在库', 2)
        resp = self._assign(authenticated_client, branch, item,
                            {'item': str(item.id), '数量': 2, '使用人': '张三'})
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert '必须选择与数量等长的实例' in str(resp.data['detail'])

    def test_instance_count_mismatch_rejected(self, authenticated_client, branch):
        item = _item('IB-002')
        _seed(branch, item, stock=2)
        insts = _make_instances(branch, item, '在库', 2)
        resp = self._assign(authenticated_client, branch, item, {
            'item': str(item.id), '数量': 2,
            'instances': [str(insts[0].id)], '使用人': '张三',
        })
        assert resp.status_code == 400
        assert '不一致' in str(resp.data['detail'])

    def test_quantity_item_with_instances_rejected(self, authenticated_client, branch):
        item = _item('IB-Q-001', management_type='quantity')
        _seed(branch, item, stock=1)
        other = _item('IB-Q-002')
        insts = _make_instances(branch, other, '在库', 1)
        resp = self._assign(authenticated_client, branch, item,
                            _line(item, insts, 使用人='张三'))
        assert resp.status_code == 400
        assert '非实例管理品目无需选择实例' in str(resp.data['detail'])

    def test_purchase_with_instances_rejected(self, authenticated_client, branch):
        item = _item('IB-P-001')
        insts = _make_instances(branch, item, '在库', 1)
        resp = authenticated_client.post('/api/transfers/purchase', {
            '调拨日期': '2026-08-23', '调出分公司': branch.name,
            'items': [_line(item, insts)],
        }, format='json')
        assert resp.status_code == 400
        assert '自动生成' in str(resp.data['detail'])

    def test_source_state_mismatch_rejected(self, authenticated_client, branch):
        item = _item('IB-003')
        _seed(branch, item, recycle=1)
        insts = _make_instances(branch, item, '回收库', 1)
        resp = self._assign(authenticated_client, branch, item,
                            _line(item, insts, 使用人='张三'))  # 默认来源=新品库，要求在库态
        assert resp.status_code == 400
        assert '不是 在库' in str(resp.data['detail'])

    def test_assign_requires_user(self, authenticated_client, branch):
        item = _item('IB-004')
        _seed(branch, item, stock=1)
        insts = _make_instances(branch, item, '在库', 1)
        resp = self._assign(authenticated_client, branch, item, _line(item, insts))
        assert resp.status_code == 400
        assert '使用人' in str(resp.data['detail'])

    def test_branch_mismatch_rejected(self, authenticated_client, branch, second_branch):
        item = _item('IB-005')
        _seed(branch, item, stock=1)
        _seed(second_branch, item, stock=1)
        insts = _make_instances(second_branch, item, '在库', 1)
        resp = self._assign(authenticated_client, branch, item,
                            _line(item, insts, 使用人='张三'))
        assert resp.status_code == 400
        assert '不在' in str(resp.data['detail'])

    def test_duplicate_reference_in_doc_rejected(self, authenticated_client, branch):
        item = _item('IB-006')
        _seed(branch, item, stock=1)
        insts = _make_instances(branch, item, '在库', 1)
        dept_id = str(_dept(branch).id)
        resp = authenticated_client.post('/api/transfers/assign', {
            '调拨日期': '2026-08-23', '调出分公司': branch.name,
            'items': [_line(item, insts, 使用人='甲', department=dept_id),
                      _line(item, insts, 使用人='乙', department=dept_id)],
        }, format='json')
        assert resp.status_code == 400
        assert '重复引用' in str(resp.data['detail'])

    def test_valid_assign_returns_instance_links(self, authenticated_client, branch):
        item = _item('IB-007')
        _seed(branch, item, stock=2)
        insts = _make_instances(branch, item, '在库', 2)
        resp = self._assign(authenticated_client, branch, item,
                            _line(item, insts, 使用人='张三'))
        assert resp.status_code == 201
        line = resp.data['lines'][0]
        assert [i['code'] for i in line['instances']] == \
            [i.内部编号 for i in insts]


# ---------------------------------------------------------------------------
# 五单实例迁移矩阵（生效事务内）
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestDocumentInstanceMatrix:
    def test_purchase_generates_instances(self, authenticated_client, branch):
        item = _item('IM-P-001')
        resp = authenticated_client.post('/api/transfers/purchase', {
            '调拨日期': '2026-08-23', '调出分公司': branch.name,
            'items': [{'item': str(item.id), '数量': 3}],
        }, format='json')
        assert resp.status_code == 201
        assert _approve(authenticated_client, resp.data['id']).status_code == 200
        insts = list(FixedAsset.objects.filter(item=item).order_by('内部编号'))
        assert [i.内部编号 for i in insts] == \
            ['IM-P-001-1', 'IM-P-001-2', 'IM-P-001-3']
        assert all(i.当前状态 == '在库' for i in insts)
        assert all(i.birth_line is not None for i in insts)
        assert all(i.branch_id == branch.id for i in insts)
        assert InstanceSequence.objects.get(item=item).last_no == 3

    def test_purchase_sequence_continues(self, authenticated_client, branch):
        item = _item('IM-P-002')
        _seed(branch, item, stock=1)
        _make_instances(branch, item, '在库', 2)  # 既有 IM-P-002-1/2
        resp = authenticated_client.post('/api/transfers/purchase', {
            '调拨日期': '2026-08-23', '调出分公司': branch.name,
            'items': [{'item': str(item.id), '数量': 1}],
        }, format='json')
        assert resp.status_code == 201
        _approve(authenticated_client, resp.data['id'])
        assert FixedAsset.objects.filter(内部编号='IM-P-002-3').exists()

    def test_assign_stock_binds_user(self, authenticated_client, branch):
        from apps.organizations.models import Department
        item = _item('IM-A-001')
        _seed(branch, item, stock=2)
        insts = _make_instances(branch, item, '在库', 2)
        dept = Department.objects.create(branch=branch, name='行政部')
        resp = authenticated_client.post('/api/transfers/assign', {
            '调拨日期': '2026-08-23', '调出分公司': branch.name,
            'items': [_line(item, insts, 使用人='张三', department=str(dept.id))],
        }, format='json')
        assert resp.status_code == 201
        assert _approve(authenticated_client, resp.data['id']).status_code == 200
        for inst in insts:
            inst.refresh_from_db()
            assert inst.当前状态 == '在用'
            assert inst.使用人 == '张三'
            assert inst.department_id == dept.id
        row = AssetStock.objects.get(branch=branch, item=item)
        assert (row.在库数量, row.在用数量) == (0, 2)

    def test_assign_from_recycle_bin(self, authenticated_client, branch):
        item = _item('IM-A-002')
        _seed(branch, item, recycle=2)
        insts = _make_instances(branch, item, '回收库', 2)
        resp = authenticated_client.post('/api/transfers/assign', {
            '调拨日期': '2026-08-23', '调出分公司': branch.name,
            '领用来源': 'recycle_bin',
            'items': [_line(item, insts, 使用人='李四', department=str(_dept(branch).id))],
        }, format='json')
        assert resp.status_code == 201
        assert resp.data['领用来源'] == 'recycle_bin'
        assert _approve(authenticated_client, resp.data['id']).status_code == 200
        insts[0].refresh_from_db()
        assert insts[0].当前状态 == '在用'
        row = AssetStock.objects.get(branch=branch, item=item)
        assert (row.在库数量, row.回收库数量, row.在用数量) == (0, 0, 2)

    def test_assign_insufficient_recycle_stock_rejected(self, authenticated_client, branch):
        """来源=回收库但回收库列不足 → 终检按回收库列校验并整单回滚。"""
        item = _item('IM-A-003')
        _seed(branch, item, stock=5, recycle=1)
        insts = _make_instances(branch, item, '回收库', 1)
        resp = authenticated_client.post('/api/transfers/assign', {
            '调拨日期': '2026-08-23', '调出分公司': branch.name,
            '领用来源': 'recycle_bin',
            'items': [{'item': str(item.id), '数量': 2,
                       'instances': [str(i.id) for i in insts]}],
        }, format='json')
        assert resp.status_code == 400  # 实例 1 个 ≠ 数量 2
        row = AssetStock.objects.get(branch=branch, item=item)
        assert row.在库数量 == 5 and row.回收库数量 == 1

    def test_return_clears_user(self, authenticated_client, branch):
        item = _item('IM-R-001')
        _seed(branch, item, in_use=1)
        insts = _make_instances(branch, item, '在用', 1, user='张三')
        resp = authenticated_client.post('/api/transfers/return', {
            '调拨日期': '2026-08-23', '调出分公司': branch.name,
            'items': [_line(item, insts)],
        }, format='json')
        assert resp.status_code == 201
        assert _approve(authenticated_client, resp.data['id']).status_code == 200
        insts[0].refresh_from_db()
        assert insts[0].当前状态 == '在库' and insts[0].使用人 == ''

    def test_transfer_moves_branch(self, authenticated_client, branch, second_branch):
        item = _item('IM-T-001')
        _seed(branch, item, stock=1)
        insts = _make_instances(branch, item, '在库', 1)
        resp = authenticated_client.post('/api/transfers/transfer', {
            '调拨日期': '2026-08-23', '调出分公司': branch.name,
            '调入分公司': second_branch.name,
            'items': [_line(item, insts)],
        }, format='json')
        assert resp.status_code == 201
        assert _approve(authenticated_client, resp.data['id']).status_code == 200
        insts[0].refresh_from_db()
        assert insts[0].branch_id == second_branch.id
        assert insts[0].当前状态 == '在库'

    def test_recovery_recycle_and_dispose(self, authenticated_client, branch):
        item = _item('IM-C-001')
        _seed(branch, item, in_use=2)
        keep, gone = _make_instances(branch, item, '在用', 2, user='王五')

        resp = authenticated_client.post('/api/transfers/recovery', {
            '调拨日期': '2026-08-23', '调出分公司': branch.name,
            'items': [_line(item, [keep])],
        }, format='json')
        assert resp.status_code == 201
        assert _approve(authenticated_client, resp.data['id']).status_code == 200
        keep.refresh_from_db()
        assert keep.当前状态 == '回收库' and keep.使用人 == ''

        resp = authenticated_client.post('/api/transfers/recovery', {
            '调拨日期': '2026-08-23', '调出分公司': branch.name,
            '回收去向': 'dispose', '处置方式': '出售', '处置金额': 300,
            'items': [_line(item, [gone])],
        }, format='json')
        assert resp.status_code == 201
        assert _approve(authenticated_client, resp.data['id']).status_code == 200
        gone.refresh_from_db()
        assert gone.当前状态 == '退役'
        assert FixedAsset.objects.filter(pk=gone.pk).exists()
        row = AssetStock.objects.get(branch=branch, item=item)
        assert (row.在用数量, row.回收库数量) == (0, 1)

    def test_occupied_instance_rolls_back_whole_doc(self, authenticated_client, branch):
        """创建到生效之间实例被并发单据占用 → 终检失败，台账与实例均无变化。"""
        item = _item('IM-X-001')
        _seed(branch, item, stock=1)
        insts = _make_instances(branch, item, '在库', 1)

        doc_b = authenticated_client.post('/api/transfers/assign', {
            '调拨日期': '2026-08-23', '调出分公司': branch.name,
            'items': [_line(item, insts, 使用人='乙', department=str(_dept(branch).id))],
        }, format='json')
        doc_a = authenticated_client.post('/api/transfers/assign', {
            '调拨日期': '2026-08-23', '调出分公司': branch.name,
            'items': [_line(item, insts, 使用人='甲', department=str(_dept(branch).id))],
        }, format='json')
        assert _approve(authenticated_client, doc_a.data['id']).status_code == 200

        resp = _approve(authenticated_client, doc_b.data['id'])
        assert resp.status_code == 400
        assert '不是 在库' in str(resp.data['detail'])
        insts[0].refresh_from_db()
        assert insts[0].使用人 == '甲'  # A 单的绑定保留，B 单未生效
        row = AssetStock.objects.get(branch=branch, item=item)
        assert (row.在库数量, row.在用数量) == (0, 1)
        from apps.transfers.models import Transfer
        assert Transfer.objects.get(pk=doc_b.data['id']).审批状态 == '待审批'


# ---------------------------------------------------------------------------
# 对账命令：实例不变量 + 迁移对齐
# ---------------------------------------------------------------------------

def _check():
    from django.core.management import call_command
    out = StringIO()
    try:
        call_command('check_ledger_consistency', stdout=out)
        return 0, out.getvalue()
    except SystemExit as e:
        return e.code, out.getvalue()


@pytest.mark.django_db
class TestInstanceInvariant:
    def test_instance_mirror_mismatch_detected(self, branch):
        item = _item('IV-001')
        _seed(branch, item, stock=5)
        _make_instances(branch, item, '在库', 3)  # 台账 5 ≠ 实例 3
        code, text = _check()
        assert code == 1
        assert '实例镜像' in text

    def test_aligned_state_passes(self, branch):
        item = _item('IV-002')
        _seed(branch, item, stock=3)
        _make_instances(branch, item, '在库', 3)
        code, text = _check()
        assert code == 0

    def test_quantity_item_with_instance_warns_only(self, branch):
        item = _item('IV-Q-001', management_type='quantity')
        _seed(branch, item, stock=2)
        FixedAsset.objects.create(
            item=item, 内部编号='IV-Q-001-1', 当前状态='在库', branch=branch,
        )
        code, text = _check()
        assert code == 0
        assert 'IV-Q-001' in text and '决断' in text

    def test_alignment_migration_aligns_ledger_to_instances(self, branch):
        """0019 对齐函数：以实例计数为准生成期初调整单，对齐后零差异。"""
        import importlib.util
        from apps import assets as assets_app
        spec = importlib.util.spec_from_file_location(
            'm0019_align',
            Path(assets_app.__file__).parent / 'migrations' / '0019_align_ledger_to_instances.py',
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        from django.apps import apps as real_apps
        item = _item('IV-003')
        _seed(branch, item, stock=5)   # 台账在库 5
        _make_instances(branch, item, '在库', 3)  # 实例在库 3
        _make_instances(branch, item, '在用', 1)  # 台账在用 0

        module.align(real_apps, None)

        row = AssetStock.objects.get(branch=branch, item=item)
        assert row.在库数量 == 3 and row.在用数量 == 1
        from apps.assets.models import LedgerAdjustment
        adjs = LedgerAdjustment.objects.filter(item=item, is_initial=True)
        assert any(a.事由 == '实例层接入对齐' for a in adjs)
        code, text = _check()
        assert code == 0


# ---------------------------------------------------------------------------
# 架构测试：实例写操作白名单（仅 services）
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestInstanceArchitecture:
    def test_instance_write_patterns_confined_to_service(self):
        """FixedAsset 建档/删除与状态/使用人/分公司赋值仅允许 services/migrations/tests。"""
        backend_apps = Path(__file__).resolve().parent.parent / 'apps'
        assign_re = re.compile(
            r'\b\w+\.(当前状态|使用人|branch|department)\s*=[^=]'
        )
        violations = []
        for py in backend_apps.rglob('*.py'):
            rel = py.relative_to(backend_apps)
            if any(part in ('migrations', 'services', 'tests') for part in rel.parts[:-1]):
                continue
            try:
                text = py.read_text(encoding='utf-8')
            except UnicodeDecodeError:
                continue
            if 'FixedAsset' not in text:
                continue
            for i, line in enumerate(text.splitlines(), 1):
                s = line.strip()
                if s.startswith('#') or s.startswith('"') or s.startswith("'"):
                    continue
                if ('FixedAsset.objects.' in s and any(
                        op in s for op in ('.create(', '.get_or_create(', '.update(', '.bulk_create('))
                ) or ('FixedAsset' in s and '.delete()' in s) or assign_re.search(s):
                    violations.append(f'{rel}:{i}: {s[:80]}')

        assert not violations, '实例写操作越权（铁律 2 实例版）：\n' + '\n'.join(violations)


# ---------------------------------------------------------------------------
# 存量迁移冒烟：回滚至 P1 末态造旧形状数据，前滚验证回填/对齐/对账
# ---------------------------------------------------------------------------

@pytest.mark.django_db(transaction=True)
class TestLegacyMigrationSmoke:
    def test_backfill_and_align_end_to_end(self):
        import uuid as uuid_mod
        from django.core.management import call_command
        from django.db import connection
        from apps.assets.models import AssetStock, FixedAsset, InstanceSequence, LedgerAdjustment
        from apps.categories.models import Category
        from apps.organizations.models import Branch, Region, Team

        # 组织/字典/台账不受本组迁移影响，ORM 造数（台账底数经调整单，对账口径一致）
        region = Region.objects.create(name='迁移大区', code='MGR01')
        team = Team.objects.create(name='迁移组', region=region)
        branch = Branch.objects.create(name='迁移分公司', code='MG001', team=team)
        item = Category.objects.create(
            asset_category='固定', item_category='办公', asset_name='旧笔记本',
            asset_code='NB-OLD', unit='台', management_type='instance',
        )
        ledger.apply_adjustment(branch, item, ledger.COLUMN_STOCK, 5, '测试造数')

        call_command('migrate', 'assets', '0015', verbosity=0)

        # 旧形状实例（0015 时期的列）：空闲(供应商/单价待折叠)、在库、未登记编号(须入籍存根)
        with connection.cursor() as cur:
            for inner, code, state, supplier, price in [
                ('NB-OLD-1', 'NB-OLD', '空闲', '联想', 7999),
                ('NB-OLD-2', 'NB-OLD', '在库', '', None),
                ('XX-UN-1', 'XX-UN', '在库', '', None),
            ]:
                cur.execute(
                    "INSERT INTO assets_fixedasset (id, 内部编号, 资产编号, 资产类目, 资产名称, 序列号, "
                    "供应商, 使用人, 所属部门, 当前状态, 分公司, 分公司编号, branch_id, 入库日期, 备注, "
                    "物品分类, 规格, 是否租用, 数量, 单价, 购入金额, 出库日期, created_at, updated_at) "
                    "VALUES (%s, %s, %s, '固定', '旧品', 'SN', %s, '张三', '行政部', %s, '迁移分公司', 'MG001', %s, NULL, '原备注', '办公', '', 0, 1, %s, NULL, NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
                    [uuid_mod.uuid4().hex, inner, code, supplier, state, branch.id.hex, price])

        call_command('migrate', verbosity=0)

        # 空闲 → 回收库；item 回链；历史文本折叠备注
        inst1 = FixedAsset.objects.get(内部编号='NB-OLD-1')
        assert inst1.当前状态 == '回收库'
        assert inst1.item.asset_code == 'NB-OLD'
        assert '历史档案' in inst1.备注 and '供应商=联想' in inst1.备注
        # 未登记编号自动入籍字典存根（instance 管理）
        stub = Category.objects.get(asset_code='XX-UN')
        assert stub.management_type == 'instance'
        assert FixedAsset.objects.get(内部编号='XX-UN-1').item_id == stub.id
        # 序列行初始化到存量最大序号
        assert InstanceSequence.objects.get(item__asset_code='NB-OLD').last_no == 2
        # 台账对齐：在库 5 → 实例在库 1；回收库 0 → 实例回收库 1
        row = AssetStock.objects.get(branch=branch, item__asset_code='NB-OLD')
        assert (row.在库数量, row.回收库数量) == (1, 1)
        assert LedgerAdjustment.objects.filter(
            item__asset_code='NB-OLD', is_initial=True, 事由='实例层接入对齐').count() == 2
        # 迁移完成对账零差异（数量 + 实例双不变量）
        code, text = _check()
        assert code == 0, text


# ---------------------------------------------------------------------------
# 对账警告去重 + 管理方式切换对齐命令
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestMirrorWarningDedup:
    def test_warning_one_line_per_item_with_count(self, branch):
        """同品目多实例 → 一行警告（模型默认排序不得混入 DISTINCT）。"""
        from django.core.management import call_command
        from io import StringIO
        item = _item('WD-001', management_type='quantity')
        _seed(branch, item, stock=5)
        _make_instances(branch, item, '在库', 3)
        out = StringIO()
        try:
            call_command('check_ledger_consistency', stdout=out)
        except SystemExit:
            pass
        text = out.getvalue()
        assert text.count('WD-001') == 1
        assert '3 条实例档案' in text


@pytest.mark.django_db
class TestAlignCommand:
    def test_management_type_switch_flow(self, branch):
        """决断路径：数量→实例管理切换 → 对账镜像炸 → 对齐命令 → 对账通过。"""
        from apps.categories.models import Category
        from apps.assets.models import AssetStock, FixedAsset, LedgerAdjustment
        item = _item('AL-001', management_type='quantity')
        _seed(branch, item, stock=5)          # 数量管理时代：台账在库 5
        _make_instances(branch, item, '在库', 2)  # 实际只有 2 台档案

        # 管理员决断：改为实例管理 → 实例镜像开始执法 → 对账失败
        Category.objects.filter(pk=item.pk).update(management_type='instance')
        code, text = _check()
        assert code == 1
        assert '实例镜像' in text

        # 预览：列出差异、不落单
        from django.core.management import call_command
        from io import StringIO
        out = StringIO()
        call_command('align_ledger_to_instances', stdout=out)
        preview = out.getvalue()
        assert 'AL-001' in preview and '+2' not in preview  # 5 → 2 是 -3
        assert '-3' in preview
        assert not LedgerAdjustment.objects.filter(item=item, 事由__contains='切换对齐').exists()

        # 确认执行：台账对齐实例计数（在库 5 → 2），出非期初调整单
        call_command('align_ledger_to_instances', '--confirm', stdout=StringIO())
        row = AssetStock.objects.get(branch=branch, item=item)
        assert row.在库数量 == 2
        adj = LedgerAdjustment.objects.get(item=item, 事由__contains='切换对齐')
        assert adj.变动量 == -3 and adj.is_initial is False
        code, text = _check()
        assert code == 0, text

        # 幂等：再跑无差异
        out = StringIO()
        call_command('align_ledger_to_instances', stdout=out)
        assert '已对齐' in out.getvalue()


# ---------------------------------------------------------------------------
# 存量状态归一（决断路线 A：品目维持数量管理，档案只修枚举）
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestNormalizeStatus:
    def _make_legacy(self, branch, code, state, n):
        item = _item(code, management_type='quantity')
        for i in range(n):
            FixedAsset.objects.create(
                item=item, 内部编号=f'{code}-{i + 1}', 当前状态=state, branch=branch,
            )
        return item

    def test_legacy_states_normalized(self, branch):
        from django.core.management import call_command
        from io import StringIO
        item = self._make_legacy(branch, 'NS-001', '使用中', 3)
        self._make_legacy(branch, 'NS-002', '空闲中', 2)
        self._make_legacy(branch, 'NS-003', '维修中', 1)
        self._make_legacy(branch, 'NS-004', '已报废', 1)
        self._make_legacy(branch, 'NS-005', '在库', 1)  # 合法不动

        out = StringIO()
        call_command('normalize_instance_status', stdout=out)  # 预览不落
        assert '使用中 × 3 → 在用' in out.getvalue()
        assert FixedAsset.objects.filter(当前状态='使用中').count() == 3  # 未执行

        call_command('normalize_instance_status', '--confirm', stdout=StringIO())
        assert FixedAsset.objects.filter(当前状态='使用中').count() == 0
        assert FixedAsset.objects.filter(item__asset_code='NS-001', 当前状态='在用').count() == 3
        assert FixedAsset.objects.filter(item__asset_code='NS-002', 当前状态='回收库').count() == 2
        assert FixedAsset.objects.filter(item__asset_code='NS-003', 当前状态='在用').count() == 1
        assert FixedAsset.objects.filter(item__asset_code='NS-004', 当前状态='退役').count() == 1
        assert FixedAsset.objects.filter(item__asset_code='NS-005', 当前状态='在库').count() == 1

    def test_idempotent(self, branch):
        from django.core.management import call_command
        from io import StringIO
        self._make_legacy(branch, 'NS-006', '使用中', 2)
        call_command('normalize_instance_status', '--confirm', stdout=StringIO())
        out = StringIO()
        call_command('normalize_instance_status', stdout=out)
        assert '无需归一' in out.getvalue()

    def test_normalize_keeps_ledger_untouched(self, branch):
        """路线 A 语义：只动状态枚举，台账/单据一概不碰（数量管理品目不参与镜像）。"""
        from django.core.management import call_command
        from apps.assets.models import AssetStock, LedgerAdjustment
        item = _item('NS-007', management_type='quantity')
        _seed(branch, item, in_use=5)
        self._make_legacy(branch, 'NS-007', '使用中', 2)
        before_adj = LedgerAdjustment.objects.count()
        call_command('normalize_instance_status', '--confirm', stdout=StringIO())
        row = AssetStock.objects.get(branch=branch, item=item)
        assert row.在用数量 == 5
        assert LedgerAdjustment.objects.count() == before_adj
        code, _ = _check()
        assert code == 0


# ---------------------------------------------------------------------------
# P2 第三刀存量迁移冒烟：盘点项换挂台账行 + Asset 删表
# ---------------------------------------------------------------------------

@pytest.mark.django_db(transaction=True)
class TestThirdCutMigrationSmoke:
    def test_inventory_remap_and_asset_drop(self):
        import uuid as uuid_mod
        from django.core.management import call_command
        from django.db import connection
        from apps.assets.models import AssetStock
        from apps.categories.models import Category
        from apps.inventories.models import InventoryTask, InventoryItem
        from apps.organizations.models import Branch, Region, Team
        from apps.assets.services import ledger

        region = Region.objects.create(name='三大区', code='TC01')
        team = Team.objects.create(name='三组', region=region)
        branch = Branch.objects.create(name='三分公司', code='TC001', team=team)
        item = Category.objects.create(
            asset_category='固定', item_category='办公', asset_name='三刀品目',
            asset_code='TC-001', unit='台', management_type='quantity',
        )
        ledger.apply_adjustment(branch, item, ledger.COLUMN_STOCK, 4, '造数')
        stock = AssetStock.objects.get(branch=branch, item=item)
        task = InventoryTask.objects.create(name='三刀盘点', branch=branch, status='in_progress')

        call_command('migrate', 'inventories', '0003', verbosity=0)
        call_command('migrate', 'assets', '0019', verbosity=0)

        # 旧形状：Asset 行（一条可解析 / 一条脏编号）+ 盘点项挂 Asset
        asset_cols = (
            "id, 序号, 分公司, 分公司编号, branch_id, 资产编号, 资产类目, 物品分类, "
            "资产名称, 规格, 供应商, 入库日期, 是否租用, 数量, 所属部门, 使用人, "
            "当前状态, 是否充足, 电脑序列号, 备注, created_at, updated_at"
        )
        asset_vals = (
            "%s, %s, '三分公司', 'TC001', %s, %s, '固定', '办公', %s, '', '', NULL, 0, %s, "
            "'', '', '在库', 1, '', '', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP"
        )
        with connection.cursor() as cur:
            good_id = uuid_mod.uuid4().hex
            dirty_id = uuid_mod.uuid4().hex
            cur.execute(
                f"INSERT INTO assets_asset ({asset_cols}) VALUES ({asset_vals})",
                [good_id, 1, branch.id.hex, 'TC-001', '旧品', 4],
            )
            cur.execute(
                f"INSERT INTO assets_asset ({asset_cols}) VALUES ({asset_vals})",
                [dirty_id, 2, branch.id.hex, 'DIRTY-XXX', '脏品', 1],
            )
            for aid in (good_id, dirty_id):
                cur.execute(
                    "INSERT INTO inventories_item (id, task_id, asset_id, expected_qty, actual_qty, "
                    "result, check_count, remarks, created_at, updated_at) "
                    "VALUES (%s, %s, %s, 4, NULL, 'unchecked', 0, '', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
                    [uuid_mod.uuid4().hex, task.id.hex, aid])

        call_command('migrate', verbosity=0)

        # 好行换挂台账行；脏行被清理
        kept = InventoryItem.objects.filter(task=task)
        assert kept.count() == 1
        assert kept.first().stock_id == stock.id
        assert kept.first().expected_qty == 4
        # Asset 表已物理删除
        with connection.cursor() as cur:
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='assets_asset'")
            assert cur.fetchone() is None
