## 1. Backend Constants & Validation Setup

- [ ] 1.1 Add `ITEM_CATEGORIES_BY_ASSET_CATEGORY` mapping to `backend/apps/categories/constants.py` with all 7 asset categories and their corresponding item categories
- [ ] 1.2 Import and export the mapping from `backend/apps/categories/__init__.py`
- [ ] 1.3 Write unit tests for the mapping to verify all asset categories have entries and no orphaned item categories

## 2. Backend Serializer Validation

- [ ] 2.1 Update `CategorySerializer` in `backend/apps/categories/serializers.py` to change `item_category` field from CharField to ChoiceField
- [ ] 2.2 Add `validate_asset_category()` method to validate against predefined choices in the mapping
- [ ] 2.3 Add `validate_item_category()` method that checks cascade constraint: verify item_category is valid for the selected asset_category
- [ ] 2.4 Write unit tests for CategorySerializer validation (valid values, invalid values, cascade violations)

## 3. Backend API Endpoint

- [ ] 3.1 Create viewset method `get_item_categories()` in `backend/apps/categories/views.py` to handle GET `/api/categories/item-categories/?asset_category=<value>`
- [ ] 3.2 Implement request parameter validation (asset_category is required) and error handling (400 for invalid/missing)
- [ ] 3.3 Return response in format: `{ "asset_category": "...", "item_categories": [...] }`
- [ ] 3.4 Add URL routing for the new endpoint in `backend/apps/categories/urls.py`
- [ ] 3.5 Write integration tests for the endpoint (valid asset category, missing parameter, invalid asset category)

## 4. Frontend Constants Layer

- [ ] 4.1 Add `ITEM_CATEGORIES_BY_ASSET_CATEGORY` mapping to `frontend/src/constants/index.ts` mirroring the backend mapping
- [ ] 4.2 Write TypeScript tests verifying the mapping has all asset categories and covers all item categories

## 5. Frontend Form Component Updates

- [ ] 5.1 Update `CategoryForm.vue` to change item classification from `<input type="text">` to `<select>` with empty initial state
- [ ] 5.2 Update `CategoryCreate.vue` similarly (if item classification implementation differs)
- [ ] 5.3 Add `watch` on asset_category field that: calls API to fetch item_categories, updates dropdown options, clears item_category selection

## 6. Frontend API Layer

- [ ] 6.1 Add `getItemCategories(assetCategory: string)` function to `frontend/src/api/categories.ts`
- [ ] 6.2 Function calls GET `/api/categories/item-categories/?asset_category=<value>` and returns parsed response
- [ ] 6.3 Write unit tests for the API function (successful response, error handling)

## 7. Frontend Integration Testing

- [ ] 7.1 Test new category form: select asset category, verify item classification dropdown updates with correct options
- [ ] 7.2 Test edit category form: change asset category, verify item classification resets and dropdown updates
- [ ] 7.3 Test form submission with valid cascade selection (asset category → item category)
- [ ] 7.4 Test error handling: backend returns 400 when cascade constraint violated, form shows error message

## 8. Database Migration (PostgreSQL)

- [ ] 8.1 Create Django migration file to add choices constraint to `item_category` field (use `atomic=False` for PG safety)
- [ ] 8.2 Update Category model in `backend/apps/categories/models.py` to add choices to `item_category` field
- [ ] 8.3 Verify migration runs cleanly on both SQLite (dev) and PostgreSQL (production schema)

## 9. Verification & Documentation

- [ ] 9.1 Run full backend test suite: `pytest` - ensure no regressions
- [ ] 9.2 Run full frontend test suite: `npm run test` - ensure no regressions
- [ ] 9.3 Run `npm run build` to verify TypeScript type checking passes
- [ ] 9.4 Run `python manage.py check_ledger_consistency` to verify ledger checks pass
- [ ] 9.5 Document the cascade mapping in code comments explaining the asset category → item category relationships
