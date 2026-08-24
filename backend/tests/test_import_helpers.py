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
    """资产导入已下线（410）；友好错误逻辑保留给台账增量导入（见 test_asset_summary）。"""

    def test_import_returns_404(self, authenticated_client):
        from django.core.files.uploadedfile import SimpleUploadedFile
        resp = authenticated_client.post(
            '/api/assets/import',
            {'file': SimpleUploadedFile('t.xlsx', b'x')},
            format='multipart',
        )
        assert resp.status_code == 404


