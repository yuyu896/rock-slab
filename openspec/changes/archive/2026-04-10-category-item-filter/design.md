## Context

后端 `CategoryFilterSet` 已定义 `物品分类 = django_filters.CharFilter(field_name='item_category')`，支持精确匹配过滤。前端 API `getCategories` 的 params 类型也支持传入 `物品分类` 参数。只需在 Category.vue 筛选区增加下拉组件和联动逻辑。

当前 `allCategories`（全量数据）已用于统计卡片和一级分类筛选器，同样可用于提取二级分类选项。

## Goals / Non-Goals

**Goals:**
- 筛选区新增"物品分类"下拉选择器
- 与"资产类目"联动：选了一级后二级只显示对应项
- 选择后触发后端服务端过滤
- 一级分类变更时自动清空二级分类选择

**Non-Goals:**
- 不修改后端代码
- 不修改 API 函数签名（已支持）
- 不修改分页或统计逻辑

## Decisions

### 1. 物品分类选项来源：从 allCategories 计算

**选择**：基于 `allCategories` 全量数据 computed 生成二级分类选项
**理由**：`allCategories` 已有全量数据，无需额外请求。如果选了一级分类，从中过滤出对应的二级分类即可。

### 2. 联动逻辑：一级变更时重置二级

**选择**：watch `filterCategory` 变更时自动清空 `filterItemCategory`
**理由**：选择新的一级分类后，旧的二级分类值可能不属于新的一级分类，应清空让用户重新选择。

## Risks / Trade-offs

- **二级分类选项过多**：如果某个一级分类下有大量二级分类，下拉列表会较长 → 可接受，分类体系通常是有限的
