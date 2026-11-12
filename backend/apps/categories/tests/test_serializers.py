"""Tests for CategorySerializer validation."""
import pytest
from rest_framework.exceptions import ValidationError
from apps.categories.serializers import CategorySerializer


@pytest.mark.django_db
class TestCategorySerializerValidation:
    """Test validation methods in CategorySerializer."""

    def test_validate_asset_category_valid(self):
        """Valid asset categories pass validation."""
        serializer = CategorySerializer()
        valid_categories = [
            '固定资产类',
            '低值易耗品类',
            '无形资产类',
            '文档资料类',
            '特殊设备类',
            '其他资产',
        ]
        for category in valid_categories:
            result = serializer.validate_asset_category(category)
            assert result == category

    def test_validate_asset_category_invalid(self):
        """Invalid asset categories raise ValidationError."""
        serializer = CategorySerializer()
        with pytest.raises(ValidationError) as exc_info:
            serializer.validate_asset_category('不存在的类目')
        assert '资产类目必须是以下之一' in str(exc_info.value)

    def test_validate_item_category_valid_cascade(self):
        """Valid item category for selected asset category passes."""
        data = {'asset_category': '固定资产类', 'item_category': '办公设备'}
        serializer = CategorySerializer(data=data)
        result = serializer.validate_item_category('办公设备')
        assert result == '办公设备'

    def test_validate_item_category_invalid_cascade(self):
        """Item category not in asset category's list raises ValidationError."""
        data = {'asset_category': '固定资产类', 'item_category': '办公耗材'}
        serializer = CategorySerializer(data=data)
        with pytest.raises(ValidationError) as exc_info:
            serializer.validate_item_category('办公耗材')
        assert '物品分类必须是 固定资产类 下的以下之一' in str(exc_info.value)

    def test_validate_item_category_missing_asset_category(self):
        """Validating item_category without asset_category raises ValidationError."""
        data = {'item_category': '办公设备'}
        serializer = CategorySerializer(data=data)
        with pytest.raises(ValidationError) as exc_info:
            serializer.validate_item_category('办公设备')
        assert '必须先选择资产类目' in str(exc_info.value)

    def test_validate_item_category_invalid_asset_category(self):
        """Validating item_category with invalid asset_category raises ValidationError."""
        data = {'asset_category': '不存在的类目', 'item_category': '办公设备'}
        serializer = CategorySerializer(data=data)
        with pytest.raises(ValidationError) as exc_info:
            serializer.validate_item_category('办公设备')
        assert '所选资产类目无效' in str(exc_info.value)

    def test_all_valid_cascades(self):
        """Test all valid asset_category -> item_category combinations."""
        valid_combinations = [
            ('固定资产类', '办公设备'),
            ('固定资产类', '电子设备'),
            ('固定资产类', '特殊设备'),
            ('低值易耗品类', '办公耗材'),
            ('低值易耗品类', '清洁用品'),
            ('低值易耗品类', '其他消耗品'),
            ('无形资产类', '软件与数据'),
            ('文档资料类', '行政文件'),
            ('特殊设备类', '安防设备'),
            ('其他资产', '其他'),
        ]
        for asset_category, item_category in valid_combinations:
            data = {'asset_category': asset_category, 'item_category': item_category}
            serializer = CategorySerializer(data=data)
            result = serializer.validate_item_category(item_category)
            assert result == item_category
