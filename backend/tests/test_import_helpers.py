"""
Tests for import helpers and asset import error friendliness.
"""
import pytest
from datetime import date


class TestExcelDateToPython:
    def test_excel_serial(self):
        from apps.assets.utils.import_helpers import excel_date_to_python
        result = excel_date_to_python(46057)
        assert result == date(2026, 2, 4)

    def test_string_iso(self):
        from apps.assets.utils.import_helpers import excel_date_to_python
        result = excel_date_to_python('2026-03-15')
        assert result == date(2026, 3, 15)

    def test_string_slash(self):
        from apps.assets.utils.import_helpers import excel_date_to_python
        result = excel_date_to_python('2026/03/15')
        assert result == date(2026, 3, 15)

    def test_none(self):
        from apps.assets.utils.import_helpers import excel_date_to_python
        assert excel_date_to_python(None) is None

    def test_empty_string(self):
        from apps.assets.utils.import_helpers import excel_date_to_python
        assert excel_date_to_python('') is None

    def test_date_passthrough(self):
        from apps.assets.utils.import_helpers import excel_date_to_python
        d = date(2025, 6, 1)
        assert excel_date_to_python(d) is d


class TestParseBoolCn:
    def test_yes(self):
        from apps.assets.utils.import_helpers import parse_bool_cn
        assert parse_bool_cn('是') is True

    def test_no(self):
        from apps.assets.utils.import_helpers import parse_bool_cn
        assert parse_bool_cn('否') is False

    def test_none(self):
        from apps.assets.utils.import_helpers import parse_bool_cn
        assert parse_bool_cn(None) is False

    def test_empty(self):
        from apps.assets.utils.import_helpers import parse_bool_cn
        assert parse_bool_cn('') is False

    def test_bool_passthrough(self):
        from apps.assets.utils.import_helpers import parse_bool_cn
        assert parse_bool_cn(True) is True
        assert parse_bool_cn(False) is False


class TestParseDecimalSafe:
    def test_normal_number(self):
        from apps.assets.utils.import_helpers import parse_decimal_safe
        val, err = parse_decimal_safe(65, '单价')
        assert val is not None
        assert float(val) == 65.0
        assert err is None

    def test_string_number(self):
        from apps.assets.utils.import_helpers import parse_decimal_safe
        val, err = parse_decimal_safe('99.5', '单价')
        assert val is not None
        assert float(val) == 99.5
        assert err is None

    def test_slash_skipped(self):
        from apps.assets.utils.import_helpers import parse_decimal_safe
        val, err = parse_decimal_safe('/', '单价')
        assert val is None
        assert err is None

    def test_alpha_invalid(self):
        from apps.assets.utils.import_helpers import parse_decimal_safe
        val, err = parse_decimal_safe('abc', '单价')
        assert val is None
        assert '不是有效数字' in err
        assert '单价' in err

    def test_none(self):
        from apps.assets.utils.import_helpers import parse_decimal_safe
        val, err = parse_decimal_safe(None, '单价')
        assert val is None
        assert err is None

    def test_empty_skip(self):
        from apps.assets.utils.import_helpers import parse_decimal_safe
        val, err = parse_decimal_safe('无', '购入金额')
        assert val is None
        assert err is None


class TestMergeErrors:
    def test_single_error(self):
        from apps.assets.utils.import_helpers import merge_errors
        result = merge_errors([(3, '资产编号重复')])
        assert result == ['第 3 行: 资产编号重复']

    def test_consecutive_merged(self):
        from apps.assets.utils.import_helpers import merge_errors
        result = merge_errors([
            (3, '资产编号重复'), (4, '资产编号重复'), (5, '资产编号重复'),
        ])
        assert len(result) == 1
        assert '3-5' in result[0]
        assert '共 3 行' in result[0]

    def test_different_errors_not_merged(self):
        from apps.assets.utils.import_helpers import merge_errors
        result = merge_errors([
            (3, '资产编号重复'), (4, '单价无效'),
        ])
        assert len(result) == 2


@pytest.mark.django_db
class TestAssetImportFriendlyErrors:
    def test_duplicate_asset_code_friendly(self, authenticated_client):
        from apps.assets.models import Asset
        Asset.objects.create(
            序号=1, 分公司='测试', 分公司编号='CS001', 资产编号='DUP-001',
            资产类目='固定', 物品分类='办公', 资产名称='已存在', 数量=1,
        )
        resp = authenticated_client.post('/api/assets/import', {
            'file': self._make_xlsx([
                [1, '测试', 'DUP-001', 'CS001', '固定', '', '', '办公', '重复', '',
                 46057, '否', 1, '/', 65, 65, 46057, '部门', '张三', '在库', 5, '否', ''],
            ]),
        }, format='multipart')
        data = resp.data
        assert data['imported'] == 0
        assert any('已存在' in e for e in data['errors'])

    def test_invalid_decimal_friendly(self, authenticated_client):
        resp = authenticated_client.post('/api/assets/import', {
            'file': self._make_xlsx([
                [1, '测试', 'DEC-001', 'CS001', '固定', '', '', '办公', '测试', '',
                 46057, '否', 1, '/', 'abc', 100, 46057, '部门', '张三', '在库', 5, '否', ''],
            ]),
        }, format='multipart')
        data = resp.data
        assert data['imported'] == 0
        assert any('单价' in e and '不是有效数字' in e for e in data['errors'])

    def _make_xlsx(self, rows):
        """Create an in-memory xlsx file with given data rows."""
        import openpyxl
        import io
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(['序号', '分公司', '资产编号', '分公司编号', '资产类目',
                    '电脑序列号', '供应商', '物品分类', '资产名称', '图片',
                    '入库日期', '是否租用', '数量', '规格', '单价',
                    '购入金额', '出库日期', '所属部门', '使用人', '当前状态',
                    '警戒线', '是否充足', '备注'])
        for row in rows:
            ws.append(row)
        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        buf.name = 'test.xlsx'
        return buf
