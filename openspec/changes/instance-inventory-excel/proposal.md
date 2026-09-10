# 实例盘点开放 Excel 模板下载与结果导入

## Why

实例盘点口径扩为全分公司后（instance-inventory-branch-wide），单任务清单可达百余台，逐台点选/扫码在线核对不再总适用——需要与台账盘点一致的线下盘闭环：下载含清单快照的模板 → 线下核对填结果 → 导入回写。当前两处主动拦截实例盘：前端按钮不渲染、后端模板/导入端点对实例盘 400。

## What Changes

- `download_template` 增实例盘分支：模板列=序号/内部编号/序列号/品目编号/品目名称/使用人/所属部门/**核对结果**/备注，预填该任务实例清单快照；核对结果列留填（已找到/未找到）
- `import_result` 增实例盘分支：按内部编号匹配清单项，读核对结果列回写——已找到→matched、未找到→missing（记核对人与时间、核对次数 +1、备注可写）；非法值/不在清单行计入行级错误跳过；与点选/扫码同口径（导入视为一次核对）
- 保留既有护栏：仅 in_progress 可导入、Excel 校验（扩展名/大小/行数）、行级错误汇总返回
- 前端去掉实例盘任务「下载模板/导入盘点表」按钮的隐藏条件（与台账盘一致显示）
- 非目标：不改点选/扫码核对；不改漏盘规则与差异处置口径

## Capabilities

### New Capabilities

（无）

### Modified Capabilities

- `inventory-item-basis`: 实例盘点新增 Excel 模板下载与结果导入要求（对齐台账盘既有能力形态）

## Impact

- **后端**: `inventories/views.py`（download_template/import_result 各加实例盘分支）
- **前端**: `InventoryTaskList.vue`（按钮 v-if）
- 测试：后端模板/导入分支用例；前端无新逻辑（按钮显隐）
