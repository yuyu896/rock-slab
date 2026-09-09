"""上传文件统一校验：扩展名、大小、行数、图片类型。

用于所有 Excel 导入与图片上传接口，防御恶意/超大文件（如 ZIP 炍弹、超时 DoS）。
校验失败抛 UploadValidationError，调用方捕获后返回 400。
"""

EXCEL_EXTENSIONS = ('.xlsx',)

DEFAULT_MAX_SIZE_MB = 10
DEFAULT_MAX_ROWS = 50000

IMAGE_CONTENT_TYPES = ('image/jpeg', 'image/png', 'image/webp')
IMAGE_MAX_SIZE_MB = 2


class UploadValidationError(ValueError):
    """上传文件未通过校验。"""


def validate_excel_upload(file, max_size_mb=DEFAULT_MAX_SIZE_MB):
    """校验扩展名与大小（不打开文件，快速失败）。

    Content-Type 不作为拒绝依据：浏览器/代理常把它改写为
    application/octet-stream，强行校验会误伤正常上传。
    """
    name = (getattr(file, 'name', '') or '').lower()
    # 仅当提供了文件名时校验扩展名；无文件名（部分测试/代理上传）交给
    # load_workbook 做内容校验——扩展名只是快速过滤，大小/行数才是主防线。
    if name and not name.endswith(EXCEL_EXTENSIONS):
        raise UploadValidationError('仅支持 .xlsx 格式的 Excel 文件')

    size = getattr(file, 'size', 0) or 0
    max_bytes = max_size_mb * 1024 * 1024
    if size and size > max_bytes:
        raise UploadValidationError(f'文件过大，最大支持 {max_size_mb}MB')


def validate_image_upload(file, max_size_mb=IMAGE_MAX_SIZE_MB):
    """校验图片类型与大小（DRF 已解析的 content_type，与头像端点同口径）。"""
    content_type = getattr(file, 'content_type', '') or ''
    if content_type not in IMAGE_CONTENT_TYPES:
        raise UploadValidationError('仅支持 JPG、PNG、WebP 格式的图片')

    size = getattr(file, 'size', 0) or 0
    max_bytes = max_size_mb * 1024 * 1024
    if size and size > max_bytes:
        raise UploadValidationError(f'图片大小不能超过 {max_size_mb}MB')


def validate_row_count(worksheet, max_rows=DEFAULT_MAX_ROWS, header_rows=1):
    """校验数据行数（在 load_workbook 之后调用，防解压炸弹级超大表）。"""
    max_row = getattr(worksheet, 'max_row', None) or 0
    data_rows = max(0, max_row - header_rows)
    if data_rows > max_rows:
        raise UploadValidationError(
            f'数据行数过多（{data_rows} 行），最大支持 {max_rows} 行'
        )
