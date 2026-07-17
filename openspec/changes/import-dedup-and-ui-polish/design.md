## Decisions

### 决策 1：固定资产导入 DB 级查重
- 每行 create 前查 `FixedAsset.objects.filter(分公司=X, 分公司编号=X, 序列号=X, 所属部门=X).exists()`，存在则跳过+提醒。
- 预加载已有四元组集合（一次查询），避免逐行查 DB。

### 决策 2：导入行数限制
- `validate_row_count` 后加判断：`if len(rows) > 200: return 400 '数据量过大'`
- 同时适用于资产导入和固定资产导入。

### 决策 3：操作按钮加大
- `.action-btn` 全局样式 padding 从 6px 12px → 8px 16px；svg 从 14-16px → 18-20px。

### 决策 4：资产列表表格固定高度
- `.table-container` 加 `max-height: calc(100vh - 340px); overflow-y: auto;`；thead sticky。

## Open Questions
（暂无。）
