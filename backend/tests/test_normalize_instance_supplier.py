"""实例供应商存量归一命令测试（instance-supplier-dict-select）。"""
import pytest
from io import StringIO
from django.core.management import call_command


def _mk(serial, supplier):
    from apps.assets.models import FixedAsset
    from apps.categories.models import Category
    cat, _ = Category.objects.get_or_create(
        asset_code='NIS-001', defaults=dict(
            asset_category='固定资产', item_category='办公设备',
            asset_name='归一测试笔记本', unit='台', management_type='instance'),
    )
    return FixedAsset.objects.create(内部编号=serial, 序列号=serial, 当前状态='在用', item=cat, 供应商=supplier)


@pytest.mark.django_db
class TestNormalizeInstanceSupplier:
    def test_dry_run_writes_nothing(self):
        _mk('NIS-A1', '小熊')
        _mk('NIS-A2', '小熊u租')
        out = StringIO()
        call_command('normalize_instance_supplier', stdout=out)
        text = out.getvalue()
        assert '2 台' in text and 'dry-run' in text
        from apps.assets.models import FixedAsset
        assert FixedAsset.objects.get(内部编号='NIS-A1').供应商 == '小熊'  # 未写入

    def test_apply_merges_aliases_idempotent(self):
        _mk('NIS-B1', '小熊')
        _mk('NIS-B2', '小熊u租')
        _mk('NIS-B3', '小熊U组')
        _mk('NIS-B4', '小熊U租')   # 已是标准名，不动
        _mk('NIS-B5', '/')          # 拿不准的，不动
        _mk('NIS-B6', '自购（苹果）')
        call_command('normalize_instance_supplier', '--apply', stdout=StringIO())

        from apps.assets.models import FixedAsset
        get = lambda sn: FixedAsset.objects.get(内部编号=sn).供应商
        assert get('NIS-B1') == '小熊U租'
        assert get('NIS-B2') == '小熊U租'
        assert get('NIS-B3') == '小熊U租'
        assert get('NIS-B4') == '小熊U租'
        assert get('NIS-B5') == '/'                 # 未命中不动
        assert get('NIS-B6') == '自购（苹果）'       # 未命中不动

        # 幂等：重跑无命中
        out = StringIO()
        call_command('normalize_instance_supplier', '--apply', stdout=out)
        assert '无别名命中' in out.getvalue()
