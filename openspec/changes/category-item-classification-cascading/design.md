## Context

**现状：**
- 前端 CategoryCreate.vue、CategoryForm.vue：资产类目已是 `<select>` 下拉（7个硬编码选项），物品分类是 `<input type="text">` 自由文本
- 后端 Category 模型：asset_category、item_category 都是 CharField，无 choices 约束
- 常量 constants/index.ts：ASSET_CATEGORY_CODES、ITEM_CATEGORY_CODES 已定义，但两者无关联映射
- 数据库：SQLite (开发/测试)、PostgreSQL (生产)，无子查询或聚合限制

**用户痛点：**
- 物品分类输入无统一标准，造成数据不一致（"办公设备" vs "办公设备类" vs "办公"）
- 后端无验证，坏数据可直接入库
- 前端无级联逻辑，用户无法快速找到对应分类

## Goals / Non-Goals

**Goals:**
- 前端：物品分类改为下拉选择，选定资产类目后自动刷新物品分类列表
- 后端：两个字段都加 ChoiceField 验证，非法值返回 400 错误
- 常量层：建立资产类目 → 物品分类的 1:n 映射关系（一次性维护）
- API：新增端点供前端查询物品分类列表（支持按资产类目过滤）
- 无破坏性改动，已有数据库记录保持不变

**Non-Goals:**
- 不涉及资产类目的新增/删除功能（保持硬编码 7 个）
- 不涉及历史数据清洗（已有的"脏数据"在查询时过滤展示，新增/修改才强制验证）
- 不涉及权限系统改动（保持现有权限策略）

## Decisions

### 1. 物品分类数据源：常量 vs 数据库
**决策：** 使用常量映射 (constants/index.ts)，不创建新数据库表

**理由：**
- 物品分类集合相对稳定，一年改动频率低
- 无"组织级自定义分类"的需求，全局统一即可
- 复杂度低，无需 ORM、迁移、API 管理
- 常量与前端 UI 选项天然同源，易于维护

**备选方案：** 创建 ItemCategoryMaster 表 → 需要额外的数据库表、迁移、权限管理，收益不足

### 2. 映射结构：ITEM_CATEGORIES_BY_ASSET_CATEGORY
**决策：** 在 constants/index.ts 新增 `Record<AssetCategoryType, string[]>` 映射

**结构示例：**
```typescript
export const ITEM_CATEGORIES_BY_ASSET_CATEGORY: Record<string, string[]> = {
  '固定资产类': ['办公设备', '电子设备', '特殊设备'],
  '低值易耗品': ['办公耗材', '清洁用品', '其他消耗品'],
  // ...其余 5 个资产类目对应的物品分类
}
```

**理由：** 避免重复定义，ITEM_CATEGORY_CODES 只声明所有可能值，ITEM_CATEGORIES_BY_ASSET_CATEGORY 声明关联关系

### 3. 后端验证时机
**决策：** CategorySerializer 中 item_category 改用 ChoiceField，choices 由 validate_item_category() 动态生成

**逻辑：**
```python
def validate_item_category(self, value):
    asset_category = self.initial_data.get('asset_category')
    valid_items = ITEM_CATEGORIES_BY_ASSET_CATEGORY.get(asset_category, [])
    if value not in valid_items:
        raise ValidationError(f'物品分类 {value} 不属于 {asset_category}')
    return value
```

**理由：** 在序列化层验证关联约束，比模型层灵活（可以访问同一请求的其他字段）

### 4. API 端点设计
**决策：** 新增 GET `/api/categories/item-categories/?asset_category=<value>` 返回过滤列表

**响应格式：**
```json
{
  "asset_category": "固定资产类",
  "item_categories": ["办公设备", "电子设备", "特殊设备"]
}
```

**理由：** 前端无需硬编码常量，后端单一数据源；支持未来迁到数据库时的平滑过渡

### 5. 前端级联逻辑
**决策：** 使用 Composition API 中的 watch 监听 asset_category 变化，触发 item_categories 刷新

**伪代码：**
```typescript
const form = reactive({ asset_category: '', item_category: '' })
const itemCategories = ref<string[]>([])

watch(() => form.asset_category, async (newAssetCategory) => {
  if (newAssetCategory) {
    const res = await api.getItemCategories(newAssetCategory)
    itemCategories.value = res.item_categories
    form.item_category = '' // 重置选择
  }
})
```

**理由：** watch 是 Vue 3 的标准模式，响应式、清晰、易测试

## Risks / Trade-offs

| 风险 | 缓解 |
|-----|-----|
| **常量维护遗漏** - 新增资产类目时忘记在映射里加对应分类 | 编写单元测试验证：所有资产类目在映射里都有对应项；所有物品分类都至少被一个资产类目引用 |
| **后端 ChoiceField 导致已有"脏数据"查询报错** | 改动仅在 create/update 时验证；GET 列表端点保持允许已有任意值（向后兼容）；新增迁移脚本可选清洗历史数据 |
| **前端级联逻辑复杂导致 bug** | watch 加详尽单元测试（监听触发、选项刷新、重置逻辑）；集成测试验证 E2E 流程 |
| **API 性能** - 每次切换资产类目都要调后端 | 响应极快（仅常量查询），且请求频率低（用户新增/编辑时偶发）；可考虑前端缓存常量列表 |

## Migration Plan

**部署步骤：**
1. 合入 constants/index.ts 映射定义
2. 后端 CategorySerializer 加验证（不破坏已有数据）
3. 新增 `/api/categories/item-categories/` API 端点
4. 前端改造 CategoryCreate.vue、CategoryForm.vue：物品分类改下拉 + watch 级联逻辑
5. 本地/测试验证：新增分类、编辑分类、级联刷新、后端拒绝非法值
6. 生产部署：数据库迁移（添加 choices 约束到 item_category 字段）

**回滚策略：**
- 代码回滚至前一版本
- 数据库：迁移有 `atomic=False`，手动 SQL 移除 choices 约束（或保留约束、后端改回不验证）

## Open Questions

- **已有脏数据的处理方案？** 提案中说"无破坏性改动"，但 ChoiceField 验证会导致某些旧记录查询时校验失败。是否需要迁移脚本对历史数据进行清洗或标记？
- **物品分类的完整映射关系？** 当前有 7 个资产类目、7 个物品分类，但关联关系未确认。是否每个资产类目都该有 3-5 个物品分类？需要产品或业务确认。
- **前端常量缓存？** 是在每次新增/编辑分类时都请求 `/api/categories/item-categories/`，还是应用启动时拉一次全量映射缓存到 Pinia？
