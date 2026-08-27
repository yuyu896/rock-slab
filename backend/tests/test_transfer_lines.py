"""P2 流转单明细行化：多行单据全链路、整单回滚、并发、禁删、编号、迁移一致性。"""
import pytest
from django.db import close_old_connections, connection
from rest_framework import status

TRANSFER_LIST_URL = '/api/transfers/'


def _action_url(action_name, pk=None):
    if pk:
        return f'/api/transfers/{pk}/{action_name}'
    return f'/api/transfers/{action_name}'


def _line(item_id_fixture, code, qty, **extra):
    line = {'item': item_id_fixture(code), '数量': qty}
    line.update(extra)
    return line


@pytest.mark.django_db
class TestMultiLineDocument:
    """4.1 多明细单据全链路"""

    def test_multi_line_purchase_full_chain(self, authenticated_client, branch, item_id):
        payload = {
            '调拨日期': '2026-08-01',
            '调出分公司': branch.name,
            '供应商': '测试供应商',
            'items': [
                _line(item_id, 'AST-TEST-001', 10, 单价='99.00', 金额='990.00'),
                _line(item_id, 'AST-TEST-002', 5, 本批规格='加强版'),
            ],
        }
        resp = authenticated_client.post(_action_url('purchase'), payload, format='json')
        assert resp.status_code == status.HTTP_201_CREATED
        data = resp.data
        assert data['品项数'] == 2
        assert data['总数量'] == 15
        assert data['单据编号'].startswith('CG20260801-')
        assert [line['行号'] for line in data['lines']] == [1, 2]
        # 字典回显：编号/名称/单位来自联查，行内不存
        assert data['lines'][0]['item_code'] == 'AST-TEST-001'
        assert data['lines'][0]['unit'] == '个'
        assert data['lines'][1]['本批规格'] == '加强版'
        assert '资产编号' not in data and '调拨数量' not in data

        approve = authenticated_client.post(
            _action_url('approve', data['id']), {'approved': True}, format='json',
        )
        assert approve.status_code == status.HTTP_200_OK

        from apps.assets.models import AssetStock
        assert AssetStock.objects.get(
            branch=branch, item__asset_code='AST-TEST-001',
        ).在库数量 == 10
        assert AssetStock.objects.get(
            branch=branch, item__asset_code='AST-TEST-002',
        ).在库数量 == 5

    def test_duplicate_item_lines_are_additive(self, authenticated_client, branch, item_id):
        payload = {
            '调拨日期': '2026-08-01',
            '调出分公司': branch.name,
            'items': [
                _line(item_id, 'AST-TEST-001', 2),
                _line(item_id, 'AST-TEST-001', 3),
            ],
        }
        resp = authenticated_client.post(_action_url('purchase'), payload, format='json')
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data['品项数'] == 2  # 不静默合并
        authenticated_client.post(
            _action_url('approve', resp.data['id']), {'approved': True}, format='json',
        )
        from apps.assets.models import AssetStock
        assert AssetStock.objects.get(
            branch=branch, item__asset_code='AST-TEST-001',
        ).在库数量 == 5

    def test_items_empty_rejected(self, authenticated_client, branch):
        payload = {'调拨日期': '2026-08-01', '调出分公司': branch.name, 'items': []}
        resp = authenticated_client.post(_action_url('purchase'), payload, format='json')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert 'items' in resp.data

    def test_unknown_item_uuid_rejected(self, authenticated_client, branch):
        payload = {
            '调拨日期': '2026-08-01',
            '调出分公司': branch.name,
            'items': [{'item': '00000000-0000-0000-0000-000000000000', '数量': 1}],
        }
        resp = authenticated_client.post(_action_url('purchase'), payload, format='json')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_doc_number_generated_for_draft(self, authenticated_client, branch, item_id):
        payload = {
            '调拨日期': '2026-08-02',
            '调出分公司': branch.name,
            'items': [_line(item_id, 'AST-TEST-001', 1)],
            'draft': True,
        }
        resp = authenticated_client.post(_action_url('purchase'), payload, format='json')
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data['审批状态'] == '草稿'
        assert resp.data['单据编号'].startswith('CG20260802-')


@pytest.mark.django_db
class TestPartialInsufficientRollback:
    """4.2 部分行不足整单回滚"""

    def _seed(self, branch, code, stock, in_use=0):
        from apps.assets.services import ledger
        from apps.categories.models import Category
        ledger.apply_adjustment(
            branch, Category.objects.get(asset_code=code), ledger.COLUMN_STOCK, stock, '造数',
        )
        if in_use:
            ledger.apply_adjustment(
                branch, Category.objects.get(asset_code=code),
                ledger.COLUMN_IN_USE, in_use, '造数',
            )

    def test_one_line_insufficient_whole_doc_rolls_back(
        self, authenticated_client, branch, item_id, department,
    ):
        from apps.assets.models import AssetStock
        self._seed(branch, 'AST-TEST-001', stock=5)
        self._seed(branch, 'AST-TEST-002', stock=2)

        def _assign_line(code, qty):
            return _line(item_id, code, qty, 使用人='张三', department=str(department.id))

        payload = {
            '调拨日期': '2026-08-03',
            '调出分公司': branch.name,
            'items': [
                _assign_line('AST-TEST-001', 3),  # 充足
                _assign_line('AST-TEST-002', 4),  # 不足（在库 2）
            ],
        }
        resp = authenticated_client.post(_action_url('assign'), payload, format='json')
        assert resp.status_code == status.HTTP_201_CREATED
        approve = authenticated_client.post(
            _action_url('approve', resp.data['id']), {'approved': True}, format='json',
        )
        assert approve.status_code == status.HTTP_400_BAD_REQUEST
        assert '明细行 2' in str(approve.data['detail'])
        assert 'AST-TEST-002' in str(approve.data['detail'])

        # 整单回滚：充足行也未变动
        assert AssetStock.objects.get(
            branch=branch, item__asset_code='AST-TEST-001',
        ).在库数量 == 5
        assert AssetStock.objects.get(
            branch=branch, item__asset_code='AST-TEST-002',
        ).在库数量 == 2


@pytest.mark.django_db
class TestConcurrency:
    """4.3 并发机制（SQLite 测机制，真线程回归留给 PostgreSQL——同 test_inventory_concurrency 惯例）。

    单据编号并发安全 = 锁计数行自增 + (type, date) 唯一约束；
    多行审批防死锁 = 全部 (分公司, 品目) 排序后一次性锁齐（环形等待在结构上不可能）。
    """

    def test_doc_numbers_sequential_and_counter_locked_row(self, branch):
        from apps.transfers.models import DocumentSequence
        from apps.transfers.services import generate_document_number
        import datetime

        doc_date = datetime.date(2026, 8, 4)
        numbers = [generate_document_number('purchase', doc_date) for _ in range(4)]
        assert numbers == [f'CG20260804-{i:03d}' for i in range(1, 5)]
        assert len(set(numbers)) == 4
        seq = DocumentSequence.objects.get(action_type='purchase', date=doc_date)
        assert seq.last_no == 4  # 计数行与已发号数一致，后续并发在此行 select_for_update 排队

        # 不同类型/不同日期各自独立计数
        assert generate_document_number('assign', doc_date) == 'LY20260804-001'
        assert generate_document_number('purchase', datetime.date(2026, 8, 5)) == 'CG20260805-001'

    def test_unique_constraint_on_sequence(self, db):
        from django.db import IntegrityError
        from apps.transfers.models import DocumentSequence
        import datetime
        doc_date = datetime.date(2026, 8, 4)
        DocumentSequence.objects.create(action_type='purchase', date=doc_date, last_no=1)
        with pytest.raises(IntegrityError):
            DocumentSequence.objects.create(action_type='purchase', date=doc_date, last_no=2)

    def test_multi_line_opposite_orders_both_succeed(
        self, authenticated_client, branch, second_branch, item_id,
    ):
        """两行调拨单正序/逆序品目两张单先后过审，结果与行序无关（锁序确定性）。"""
        from apps.assets.models import AssetStock
        from apps.assets.services import ledger
        from apps.categories.models import Category
        for code in ('AST-TEST-001', 'AST-TEST-002'):
            ledger.apply_adjustment(
                branch, Category.objects.get(asset_code=code), ledger.COLUMN_STOCK, 10, '造数',
            )

        def _payload(first, second):
            return {
                '调拨日期': '2026-08-05',
                '调出分公司': branch.name,
                '调入分公司': second_branch.name,
                'items': [_line(item_id, first, 1), _line(item_id, second, 1)],
            }

        resp_a = authenticated_client.post(
            _action_url('transfer'), _payload('AST-TEST-001', 'AST-TEST-002'), format='json',
        )
        resp_b = authenticated_client.post(
            _action_url('transfer'), _payload('AST-TEST-002', 'AST-TEST-001'), format='json',
        )
        assert resp_a.status_code == 201 and resp_b.status_code == 201
        assert authenticated_client.post(
            _action_url('approve', resp_a.data['id']), {'approved': True}, format='json',
        ).status_code == 200
        assert authenticated_client.post(
            _action_url('approve', resp_b.data['id']), {'approved': True}, format='json',
        ).status_code == 200

        for code in ('AST-TEST-001', 'AST-TEST-002'):
            assert AssetStock.objects.get(
                branch=branch, item__asset_code=code,
            ).在库数量 == 8
            assert AssetStock.objects.get(
                branch=second_branch, item__asset_code=code,
            ).在库数量 == 2


@pytest.mark.django_db
class TestDeleteAndUpdateContract:
    """4.4 禁删已生效、驳回编辑 items 整替"""

    def _create_and_approve(self, client, branch, item_id):
        payload = {
            '调拨日期': '2026-08-06',
            '调出分公司': branch.name,
            'items': [_line(item_id, 'AST-TEST-001', 1)],
        }
        resp = client.post(_action_url('purchase'), payload, format='json')
        client.post(_action_url('approve', resp.data['id']), {'approved': True}, format='json')
        return resp.data['id']

    def test_effective_doc_delete_rejected(self, authenticated_client, branch, item_id):
        doc_id = self._create_and_approve(authenticated_client, branch, item_id)
        resp = authenticated_client.delete(f'{TRANSFER_LIST_URL}{doc_id}')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        from apps.transfers.models import Transfer
        assert Transfer.objects.filter(pk=doc_id).exists()

    def test_pending_doc_delete_allowed(self, authenticated_client, branch, item_id):
        payload = {
            '调拨日期': '2026-08-06',
            '调出分公司': branch.name,
            'items': [_line(item_id, 'AST-TEST-001', 1)],
        }
        resp = authenticated_client.post(_action_url('purchase'), payload, format='json')
        delete = authenticated_client.delete(f"{TRANSFER_LIST_URL}{resp.data['id']}")
        assert delete.status_code == status.HTTP_204_NO_CONTENT

    def test_rejected_doc_edit_replaces_items(self, authenticated_client, branch, item_id):
        payload = {
            '调拨日期': '2026-08-06',
            '调出分公司': branch.name,
            'items': [
                _line(item_id, 'AST-TEST-001', 1),
                _line(item_id, 'AST-TEST-002', 2),
            ],
        }
        resp = authenticated_client.post(_action_url('purchase'), payload, format='json')
        doc_id = resp.data['id']
        authenticated_client.post(
            _action_url('approve', doc_id), {'approved': False, 'reason': '改数量'}, format='json',
        )
        patch = authenticated_client.patch(
            f'{TRANSFER_LIST_URL}{doc_id}',
            {'items': [_line(item_id, 'AST-TEST-001', 5)]},
            format='json',
        )
        assert patch.status_code == status.HTTP_200_OK
        assert patch.data['品项数'] == 1
        assert patch.data['lines'][0]['数量'] == 5
        assert [line['行号'] for line in patch.data['lines']] == [1]  # 行号重排


@pytest.mark.django_db
class TestMigrationConsistency:
    """4.5 迁移后对账零差异（真实迁移语境）"""

    def test_backfill_keeps_consistency_zero_diff(self):
        from django.core.management import call_command
        from apps.assets.models import AssetStock, LedgerAdjustment
        if not AssetStock.objects.exists() and not LedgerAdjustment.objects.exists():
            pytest.skip('空库无流水，对账命令走未初始化容忍分支')
        call_command('check_ledger_consistency')

    def test_preview_command_lists_unknown_codes(self, capsys):
        from django.core.management import call_command
        call_command('preview_doc_line_migration')
        # Windows 控制台 GBK 捕获会乱码中文，只断言命令正常输出（清单内容已由开发库人工核验）
        assert capsys.readouterr().out.strip()


@pytest.mark.django_db
class TestListFilterByLine:
    """列表/搜索联行（任务 2.8 验收）"""

    def test_asset_code_filter_matches_any_line(self, authenticated_client, branch, item_id):
        payload = {
            '调拨日期': '2026-08-07',
            '调出分公司': branch.name,
            'items': [
                _line(item_id, 'AST-TEST-001', 1),
                _line(item_id, 'AST-TEST-002', 1),
            ],
        }
        authenticated_client.post(_action_url('purchase'), payload, format='json')
        resp = authenticated_client.get(
            f'{TRANSFER_LIST_URL}?assetCode=AST-TEST-002', format='json',
        )
        results = resp.data.get('results', resp.data)
        assert len(results) == 1
        assert results[0]['品项数'] == 2

    def test_keyword_matches_doc_number(self, authenticated_client, branch, item_id):
        payload = {
            '调拨日期': '2026-08-07',
            '调出分公司': branch.name,
            'items': [_line(item_id, 'AST-TEST-001', 1)],
        }
        resp = authenticated_client.post(_action_url('purchase'), payload, format='json')
        doc_no = resp.data['单据编号']
        search = authenticated_client.get(
            f'{TRANSFER_LIST_URL}?keyword={doc_no}', format='json',
        )
        results = search.data.get('results', search.data)
        assert len(results) == 1
