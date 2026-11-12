"""Tests for category constants."""
import pytest
from apps.categories import ITEM_CATEGORIES_BY_ASSET_CATEGORY


class TestItemCategoriesByAssetCategory:
    """Test the cascading item categories mapping."""

    def test_mapping_contains_all_asset_categories(self):
        """All expected asset categories have entries in the mapping."""
        expected_asset_categories = {
            '固定资产类',
            '低值易耗品类',
            '无形资产类',
            '文档资料类',
            '特殊设备类',
            '其他资产',
        }
        actual_asset_categories = set(ITEM_CATEGORIES_BY_ASSET_CATEGORY.keys())
        assert expected_asset_categories == actual_asset_categories

    def test_each_asset_category_has_nonempty_item_list(self):
        """Each asset category maps to a non-empty list of item categories."""
        for asset_category, item_categories in ITEM_CATEGORIES_BY_ASSET_CATEGORY.items():
            assert isinstance(item_categories, list), (
                f"Asset category '{asset_category}' maps to {type(item_categories)}, "
                "expected list"
            )
            assert len(item_categories) > 0, (
                f"Asset category '{asset_category}' has empty item list"
            )

    def test_item_categories_are_strings(self):
        """All item categories are strings."""
        for asset_category, item_categories in ITEM_CATEGORIES_BY_ASSET_CATEGORY.items():
            for item_category in item_categories:
                assert isinstance(item_category, str), (
                    f"Asset category '{asset_category}' contains non-string "
                    f"item category: {repr(item_category)}"
                )

    def test_specific_asset_category_mappings(self):
        """Verify specific asset category to item category mappings."""
        assert ITEM_CATEGORIES_BY_ASSET_CATEGORY['固定资产类'] == [
            '办公设备',
            '电子设备',
            '特殊设备',
        ]
        assert ITEM_CATEGORIES_BY_ASSET_CATEGORY['低值易耗品类'] == [
            '办公耗材',
            '清洁用品',
            '其他消耗品',
        ]
        assert ITEM_CATEGORIES_BY_ASSET_CATEGORY['无形资产类'] == ['软件与数据']
        assert ITEM_CATEGORIES_BY_ASSET_CATEGORY['文档资料类'] == ['行政文件']
        assert ITEM_CATEGORIES_BY_ASSET_CATEGORY['特殊设备类'] == ['安防设备']
        assert ITEM_CATEGORIES_BY_ASSET_CATEGORY['其他资产'] == ['其他']

    def test_no_orphaned_item_categories(self):
        """Each item category is unique to its asset category (no cross-mapping)."""
        all_item_categories = []
        for item_list in ITEM_CATEGORIES_BY_ASSET_CATEGORY.values():
            all_item_categories.extend(item_list)

        unique_item_categories = set(all_item_categories)
        assert len(unique_item_categories) == len(all_item_categories), (
            "Some item categories appear in multiple asset categories"
        )
