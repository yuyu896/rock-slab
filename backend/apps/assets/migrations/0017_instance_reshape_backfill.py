"""P2 第二刀 DML：存量实例回填——字典存根入籍、item/department 回链、空闲→回收库、
历史文本折叠备注、实例编号序列初始化（纯 Python 聚合，禁数据库特定聚合）。"""
import re

from django.db import migrations


def backfill(apps, schema_editor):
    Category = apps.get_model('categories', 'Category')
    Department = apps.get_model('organizations', 'Department')
    FixedAsset = apps.get_model('assets', 'FixedAsset')
    InstanceSequence = apps.get_model('assets', 'InstanceSequence')

    instances = list(FixedAsset.objects.all())

    # 1) 字典存根：编号不在字典的实例行自动入籍（编号户籍原则，第一刀先例）
    known_codes = set(Category.objects.values_list('asset_code', flat=True))
    for code in sorted({i.资产编号 for i in instances} - known_codes):
        name = next(
            (i.资产名称 for i in instances if i.资产编号 == code and i.资产名称),
            code,
        )
        Category.objects.create(
            asset_code=code,
            asset_name=name,
            asset_category='未分类',
            item_category='未分类',
            unit='件',
            management_type='instance',
        )
        known_codes.add(code)

    item_by_code = {
        c.asset_code: c for c in Category.objects.only('id', 'asset_code')
    }
    dept_by_key = {
        (d.branch_id, d.name): d
        for d in Department.objects.only('id', 'branch_id', 'name')
    }

    max_seq = {}  # item_code -> 最大序号
    for inst in instances:
        # 2) item 回链
        item = item_by_code.get(inst.资产编号)
        if item is not None:
            inst.item_id = item.id

        # 3) 空闲 → 回收库（语义即回收入库待再分配）
        if inst.当前状态 == '空闲':
            inst.当前状态 = '回收库'

        # 4) 部门文本 → 字典 FK（分公司内同名匹配），未匹配折叠备注
        dept_text = (inst.所属部门 or '').strip()
        if dept_text:
            dept = dept_by_key.get((inst.branch_id, dept_text))
            if dept is not None:
                inst.department_id = dept.id
            else:
                inst.备注 = _fold(inst.备注, f'所属部门={dept_text}')

        # 5) 供应商/单价/购入金额 折叠备注（无出生行的历史档案，出生信息改经出生行派生）
        legacy = []
        if (inst.供应商 or '').strip():
            legacy.append(f'供应商={inst.供应商.strip()}')
        if inst.单价 is not None:
            legacy.append(f'单价={inst.单价}')
        if inst.购入金额 is not None:
            legacy.append(f'购入金额={inst.购入金额}')
        if legacy:
            inst.备注 = _fold(inst.备注, '、'.join(legacy))

        # 6) 编号序列最大值（纯 Python 解析 `{品目编号}-{序号}` 后缀）
        m = re.match(r'^(.*)-(\d+)$', inst.内部编号 or '')
        if m and m.group(1) == inst.资产编号:
            seq = int(m.group(2))
            if seq > max_seq.get(inst.资产编号, 0):
                max_seq[inst.资产编号] = seq

        inst.save()

    # 7) 初始化实例编号序列行
    for code, seq in max_seq.items():
        item = item_by_code.get(code)
        if item is not None:
            InstanceSequence.objects.get_or_create(item_id=item.id, defaults={'last_no': seq})


def _fold(备注, fragment):
    prefix = f'历史档案：{fragment}'
    if 备注:
        return f'{prefix}；{备注}'
    return prefix


class Migration(migrations.Migration):

    atomic = False

    dependencies = [
        ('assets', '0016_instance_reshape_ddl'),
    ]

    operations = [
        migrations.RunPython(backfill, migrations.RunPython.noop),
    ]
