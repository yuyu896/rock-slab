"""transfer-import-strictness：数量严格解析（空/小数/非正报错）+ 指纹原子占位。"""
import io

import openpyxl
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status

_PURCHASE_HEADERS = ['采购日期', '分公司', '资产编号', '规格型号',
                     '供应商', '采购数量', '单价', '需求部门', '备注']
_PURCHASE_SAMPLE = ['2026-03-01', '测试分公司', 'PUR-001', '规格X',
                    '供应商A', 10, 50.0, '研发部', '采购备注']


def _purchase_file(qty):
    row = list(_PURCHASE_SAMPLE)
    row[_PURCHASE_HEADERS.index('采购数量')] = qty
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(_PURCHASE_HEADERS)
    ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    return SimpleUploadedFile('import.xlsx', buf.getvalue(), content_type='application/vnd.ms-excel')


def _upload(client, buf):
    return client.post('/api/transfers/import', {'file': buf},
                       format='multipart', QUERY_STRING='type=purchase')


@pytest.fixture
def admin_client(admin_user):
    from conftest import _client_for
    return _client_for(admin_user)


@pytest.fixture(autouse=True)
def _seed_dictionary(db, branch):
    """样例行依赖：测试分公司（conftest branch 即此名）+ 品目 PUR-001。"""
    from apps.categories.models import Category
    Category.objects.get_or_create(
        asset_code='PUR-001',
        defaults={'asset_category': '导入测试', 'item_category': '办公',
                  'asset_name': '严格解析品目', 'unit': '件', 'management_type': 'quantity'},
    )


@pytest.mark.django_db
class TestQtyStrictness:
    def test_empty_qty_row_errors(self, admin_client):
        resp = _upload(admin_client, _purchase_file(''))
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['imported'] == 0
        assert any('数量必须为正整数' in e for e in resp.data['errors'])

    def test_decimal_qty_row_errors(self, admin_client):
        resp = _upload(admin_client, _purchase_file(2.9))
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['imported'] == 0
        assert any('数量必须为正整数' in e for e in resp.data['errors'])

    def test_zero_qty_row_errors(self, admin_client):
        # 旧实现 0 会被 falsy 判定默认成 1——严格化后报错
        resp = _upload(admin_client, _purchase_file(0))
        assert resp.status_code == status.HTTP_200_OK
        assert any('数量必须为正整数' in e for e in resp.data['errors'])

    def test_integer_float_qty_accepted(self, admin_client):
        from apps.transfers.models import Transfer
        resp = _upload(admin_client, _purchase_file(5.0))
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['imported'] == 1
        assert Transfer.objects.filter(action_type='purchase').first().lines.first().数量 == 5


@pytest.mark.django_db
class TestFingerprintAtomicClaim:
    def test_same_file_second_upload_rejected(self, admin_client):
        # 同内容各造新上传对象（复用同一 SimpleUploadedFile 会因指针耗尽解析失败）
        first = _upload(admin_client, _purchase_file(10))
        assert first.status_code == status.HTTP_200_OK
        assert first.data['imported'] == 1

        second = _upload(admin_client, _purchase_file(10))
        assert second.status_code == status.HTTP_400_BAD_REQUEST
        assert '已导入过' in second.data['detail']
        # 双倍建单未发生
        from apps.transfers.models import Transfer
        assert Transfer.objects.filter(action_type='purchase').count() == 1

    def test_failed_rows_still_claim_fingerprint(self, admin_client):
        """行级失败也占指纹（占位不回收）：同文件重传 400，改内容（新指纹）可重传。"""
        bad = _upload(admin_client, _purchase_file(2.9))
        assert bad.status_code == status.HTTP_200_OK and bad.data['imported'] == 0
        again = _upload(admin_client, _purchase_file(2.9))
        assert again.status_code == status.HTTP_400_BAD_REQUEST
