## ADDED Requirements

### Requirement: Backend validation of asset category field

The system SHALL validate that the asset category field contains only values from the predefined set of valid asset categories.

#### Scenario: Valid asset category on create
- **WHEN** user POST /api/categories/ with `asset_category: "固定资产类"`
- **THEN** request succeeds with 201 Created and the category is stored in the database

#### Scenario: Invalid asset category on create
- **WHEN** user POST /api/categories/ with `asset_category: "invalid_category"`
- **THEN** request returns 400 Bad Request with validation error: "Invalid asset category value"

#### Scenario: Valid asset category on update
- **WHEN** user PATCH /api/categories/<id>/ with `asset_category: "低值易耗品类"`
- **THEN** request succeeds with 200 OK and the category is updated

#### Scenario: Invalid asset category on update
- **WHEN** user PATCH /api/categories/<id>/ with `asset_category: "fake_category"`
- **THEN** request returns 400 Bad Request with validation error

### Requirement: Backend validation of item classification field with cascade constraint

The system SHALL validate that the item classification field contains only values from the set of item categories valid for the selected asset category.

#### Scenario: Valid item classification for selected asset category
- **WHEN** user POST /api/categories/ with `asset_category: "固定资产类"` and `item_category: "办公设备"`
- **THEN** request succeeds with 201 Created and both fields are stored

#### Scenario: Item classification invalid for selected asset category
- **WHEN** user POST /api/categories/ with `asset_category: "固定资产类"` and `item_category: "行政文件"` (which belongs to "文档资料类")
- **THEN** request returns 400 Bad Request with validation error: "物品分类 行政文件 不属于 固定资产类"

#### Scenario: Both asset category and item classification are invalid
- **WHEN** user POST /api/categories/ with `asset_category: "invalid"` and `item_category: "invalid"`
- **THEN** request returns 400 Bad Request with validation errors for both fields

#### Scenario: Cascade validation on update
- **WHEN** user PATCH /api/categories/<id>/ to change asset_category to "低值易耗品类" but leave an incompatible item_category
- **THEN** request returns 400 Bad Request with cascade validation error

### Requirement: Validation does not break existing records with legacy data

The system SHALL accept existing category records with any asset_category and item_category values in GET requests, while enforcing new values to match the validation constraints.

#### Scenario: Read legacy data with non-standard item classification
- **WHEN** user GET /api/categories/ and existing records have item_category: "办公"
- **THEN** response includes the record as-is with the legacy value (no validation error on read)

#### Scenario: Cannot modify legacy record to new non-standard value
- **WHEN** user attempts to PATCH a legacy record to add a new non-standard item_category value
- **THEN** request returns 400 Bad Request with validation error (new values must match constraints)

#### Scenario: Can update legacy record to valid standard value
- **WHEN** user PATCH a legacy category record with item_category: "办公" to change it to `item_category: "办公设备"`
- **THEN** request succeeds with 200 OK and the value is updated

### Requirement: Serializer enforces validation on create and update

The system SHALL implement validation logic in CategorySerializer that checks both asset_category and the cascade constraint between asset_category and item_category.

#### Scenario: ChoiceField validation for asset_category
- **WHEN** serializer validates input data with an asset_category value
- **THEN** the field uses ChoiceField with the predefined list of 7 valid asset categories

#### Scenario: Dynamic validation for item_category cascade
- **WHEN** serializer validates input data with both asset_category and item_category
- **THEN** the validate_item_category() method checks that item_category is valid for the selected asset_category and raises ValidationError if not

#### Scenario: Validation error messages are clear
- **WHEN** validation fails on cascade constraint
- **THEN** the error message includes the invalid item_category value and the asset_category it was checked against, e.g., "物品分类 xyz 不属于 abc"
