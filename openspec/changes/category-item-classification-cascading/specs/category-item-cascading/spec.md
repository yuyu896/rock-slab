## ADDED Requirements

### Requirement: Frontend dropdown cascade for item classification

The system SHALL provide a dropdown select control for item classification that automatically updates its available options based on the selected asset category.

#### Scenario: Initial state with no asset category selected
- **WHEN** user opens the category create or edit form
- **THEN** item classification dropdown is empty (no options displayed) and disabled

#### Scenario: Item classification options update on asset category selection
- **WHEN** user selects "固定资产类" from asset category dropdown
- **THEN** item classification dropdown becomes enabled and displays only the item categories that belong to "固定资产类" (e.g., "办公设备", "电子设备", "特殊设备")

#### Scenario: Item classification resets on asset category change
- **WHEN** user previously selected "固定资产类" with item classification "办公设备", then changes asset category to "低值易耗品类"
- **THEN** item classification value is cleared and the dropdown refreshes to show options for the new asset category

#### Scenario: API call to fetch item categories
- **WHEN** user selects an asset category value
- **THEN** system makes a GET request to `/api/categories/item-categories/?asset_category=<value>` and receives a response with asset_category and item_categories array

### Requirement: API endpoint returns cascading item categories

The system SHALL provide an HTTP GET endpoint that returns the valid item categories for a given asset category.

#### Scenario: Valid asset category request
- **WHEN** GET `/api/categories/item-categories/?asset_category=固定资产类`
- **THEN** response returns 200 OK with JSON containing `asset_category: "固定资产类"` and `item_categories: ["办公设备", "电子设备", "特殊设备"]`

#### Scenario: Missing required parameter
- **WHEN** GET `/api/categories/item-categories/` (no asset_category parameter)
- **THEN** response returns 400 Bad Request with error message indicating asset_category parameter is required

#### Scenario: Invalid asset category value
- **WHEN** GET `/api/categories/item-categories/?asset_category=invalid_category`
- **THEN** response returns 400 Bad Request with error message indicating the asset category is not recognized

#### Scenario: Response format consistency
- **WHEN** any valid GET request to the endpoint is made
- **THEN** response JSON always contains `asset_category` (string) and `item_categories` (array of strings)

### Requirement: Item categories mapping constant is defined

The system SHALL maintain a mapping from asset categories to valid item categories in the frontend constants layer.

#### Scenario: Mapping covers all asset categories
- **WHEN** the application initializes
- **THEN** `ITEM_CATEGORIES_BY_ASSET_CATEGORY` constant is defined and contains entries for all 7 asset categories ("固定资产类", "低值易耗品类", "无形资产类", "文档资料类", "特殊设备类", "其他资产", "其他")

#### Scenario: Each asset category maps to valid item categories
- **WHEN** accessing `ITEM_CATEGORIES_BY_ASSET_CATEGORY["固定资产类"]`
- **THEN** the value is an array of strings matching the exact item category names (e.g., ["办公设备", "电子设备", "特殊设备"])

#### Scenario: No item category belongs to multiple asset categories
- **WHEN** the application validates the mapping
- **THEN** each item category string in `ITEM_CATEGORY_CODES` appears in at least one asset category's array
