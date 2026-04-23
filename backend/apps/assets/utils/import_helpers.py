"""
Shared helpers for Excel batch import.
Handles type conversion from Excel values to Django model field types,
and friendly error formatting.
"""
from datetime import date, datetime
from decimal import Decimal, InvalidOperation


# Excel date origin: January 1, 1900 (serial 1).
# Excel incorrectly treats 1900 as a leap year, so serial 60 = Feb 29 (nonexistent).
# We use 1899-12-30 as origin to match openpyxl's default behavior.
_EXCEL_DATE_ORIGIN = date(1899, 12, 30)

_BOOL_TRUE = {'是', 'true', 'True', 'TRUE', '1', 'yes', 'Yes', 'YES'}
_BOOL_FALSE = {'否', 'false', 'False', 'FALSE', '0', 'no', 'No', 'NO', ''}


def excel_date_to_python(val):
    """Convert an Excel date value to a Python date.

    Accepts: int (Excel serial), str ("2026-01-01"), datetime, date, None.
    Returns date or None.
    """
    if val is None:
        return None
    if isinstance(val, date) and not isinstance(val, datetime):
        return val
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, (int, float)):
        try:
            return _EXCEL_DATE_ORIGIN + __import__('datetime').timedelta(days=int(val))
        except (OverflowError, ValueError):
            return None
    if isinstance(val, str):
        val = val.strip()
        if not val:
            return None
        for fmt in ('%Y-%m-%d', '%Y/%m/%d', '%Y年%m月%d日'):
            try:
                return datetime.strptime(val, fmt).date()
            except ValueError:
                continue
        return None
    return None


def parse_bool_cn(val):
    """Convert Chinese/common boolean string to Python bool.

    "是"/"true"/"1" -> True
    "否"/"false"/"0"/empty/None -> False
    """
    if val is None:
        return False
    if isinstance(val, bool):
        return val
    s = str(val).strip()
    if s in _BOOL_TRUE:
        return True
    return False


def parse_decimal_safe(val, field_name):
    """Convert a value to Decimal. Returns (decimal_or_None, error_or_None).

    Invalid values like "/" or "无" return (None, 'XX字段值 "/" 不是有效数字').
    None/empty returns (None, None).
    """
    if val is None:
        return None, None
    if isinstance(val, (int, float)):
        return Decimal(str(val)), None
    s = str(val).strip()
    if not s or s in ('无', '/', '-', '--', 'N/A', 'n/a'):
        return None, None
    try:
        return Decimal(s), None
    except (InvalidOperation, ValueError):
        return None, f'{field_name}字段值 "{s}" 不是有效数字'


def merge_errors(row_errors):
    """Merge repeated error messages into grouped summaries.

    Input: [(row_number, message), ...]
    Output: ['第 3-26 行: 资产编号重复（共 24 行）', ...]
    """
    if not row_errors:
        return []

    groups = {}  # message -> [row_numbers]
    for row_num, msg in row_errors:
        groups.setdefault(msg, []).append(row_num)

    result = []
    for msg, rows in groups.items():
        rows.sort()
        if len(rows) == 1:
            result.append(f'第 {rows[0]} 行: {msg}')
        else:
            ranges = _collapse_ranges(rows)
            for range_str, count in ranges:
                result.append(f'第 {range_str} 行: {msg}（共 {count} 行）')
    return result


def _collapse_ranges(rows):
    """Collapse consecutive row numbers into range strings."""
    ranges = []
    start = rows[0]
    prev = rows[0]
    for r in rows[1:]:
        if r == prev + 1:
            prev = r
        else:
            count = prev - start + 1
            if count == 1:
                ranges.append((str(start), count))
            else:
                ranges.append((f'{start}-{prev}', count))
            start = r
            prev = r
    count = prev - start + 1
    if count == 1:
        ranges.append((str(start), count))
    else:
        ranges.append((f'{start}-{prev}', count))
    return ranges
