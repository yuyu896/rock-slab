## 盘点 Excel 导入 + 列表视图 — 技术设计

### 1. 后端：Excel 导入接口

文件：`apps/inventories/views.py`

#### 1.1 下载模板 `download_template`

```python
@action(detail=True, methods=['get'], url_path='import-template')
def download_template(self, request, pk=None):
```

逻辑：
- 查询该盘点任务关联的分公司和类目范围，筛选出应盘资产列表
- 生成 Excel 文件，包含列：序号、资产编号、资产名称、资产类目、账面数量、实盘数量（空）、备注（空）
- 返回文件流，Content-Type 为 xlsx

#### 1.2 导入盘点结果 `import_result`

```python
@action(detail=True, methods=['post'], url_path='import-result',
        parser_classes=[MultiPartParser])
def import_result(self, request, pk=None):
```

逻辑：
1. 校验任务状态必须为 `in_progress`
2. 用 openpyxl 解析上传的 Excel 文件
3. 逐行读取：资产编号（必填）、实盘数量（必填）、备注（选填）
4. 根据 `repeat_rule` 处理重复资产：
   - `last`：覆盖之前的实盘数量
   - `accumulate`：累加
5. 对比 `expected_qty` 和 `actual_qty`，计算 result（matched/surplus/missing）
6. 创建 `InventoryCheck` 记录
7. 返回导入结果：成功数、失败行数、错误详情列表

#### 1.3 生成盘点项（开始盘点时）

修改 `start` action，开始盘点时自动生成 InventoryItem 列表：

```python
# 筛选该分公司+类目范围下的资产，预生成盘点项
from apps.assets.models import Asset
assets = Asset.objects.all()
if task.branch:
    assets = assets.filter(分公司=task.branch.name)
if task.category:
    assets = assets.filter(资产编号__startswith=task.category.asset_code)
for asset in assets:
    InventoryItem.objects.get_or_create(
        task=task, asset=asset,
        defaults={'expected_qty': asset.数量},
    )
```

这样导入模板可以包含所有应盘资产，导入时直接更新已有 item 而非创建新的。

### 2. 前端：任务列表改为表格

文件：`frontend/src/views/Inventory.vue`

#### 2.1 结构变更

将 `<div class="task-grid">` 中的卡片循环替换为 `<table>`：

| 列 | 内容 |
|---|---|
| 任务名称 | `task.name` |
| 盘点范围 | 分公司名称 |
| 状态 | 状态标签（带颜色） |
| 漏盘规则 | 规则标签 |
| 重复规则 | 规则标签 |
| 创建时间 | `formatDate(task.created_at)` |
| 操作 | 按状态显示不同按钮组 |

操作按钮组保持与当前卡片底部一致（pending：查看/作废/开始；in_progress：查看/作废/继续；pending_review：查看/驳回/通过；等）。

#### 2.2 移除卡片相关样式

删除 `.task-grid`、`.task-card`、`.card-header`、`.card-body`、`.card-footer` 等卡片样式。新增表格样式。

### 3. 前端：Excel 导入 UI

文件：`frontend/src/views/Inventory.vue`

在 `in_progress` 状态的操作按钮中增加两个按钮：
- **下载模板**：调用 `downloadInventoryTemplate(task.id)`，触发浏览器下载
- **导入盘点表**：打开文件选择对话框，选择 xlsx 后调用 `importInventoryResult(task.id, file)`

导入完成后刷新任务列表，显示成功/失败提示。

### 4. 前端 API

文件：`frontend/src/api/inventories.ts`

```typescript
/** 下载盘点模板 */
export function downloadInventoryTemplate(id: string) {
  return request.get(`/api/inventories/${id}/import-template`, { responseType: 'blob' })
}

/** 导入盘点结果 */
export function importInventoryResult(id: string, file: File) {
  const formData = new FormData()
  formData.append('file', file)
  return request.post(`/api/inventories/${id}/import-result`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}
```

### 5. 保留扫码功能

当前 `check` action 和前端扫描视图（`MobileScan.vue`、`Inventory.vue` 中的 scanning 模板）代码全部保留，不做删除。仅在 PC 端的 `in_progress` 操作按钮中不突出扫码入口，等移动端接入后再启用。
