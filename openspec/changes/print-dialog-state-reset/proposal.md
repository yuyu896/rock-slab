# 打印弹窗关闭复位导出会话（print-dialog-state-reset）

## Why

打印弹窗组件常驻挂载（`visible` 只控制内部 `v-if`，实例不销毁），而 `watch(visible)` 只在打开时渲染 QR、**关闭时不复位任何状态**。用户在「导出图片」视图关闭弹窗后再次打开：直接停留在上一次的导出界面，且 `exportItems` 是上一批资产的旧图片；`exportError`（失败重试态）同理残留。另有一个竞态边角：关闭时在途的导出渲染完成后仍会写入旧结果、并把 `exporting` 置回，可能干扰重开后的新一轮导出（渲染中提示消失、按钮提前解禁）。

## What Changes

- **关闭即丢弃会话**：`visible` 变 false 时复位导出三态（`exportMode`/`exportItems`/`exportError`/`exporting`），重开必回干净的打印预览。
- **在途导出作废**：`openExport` 引入导出会话序号（session token），关闭弹窗时递增作废；过期会话的 resolve 不写 `exportItems`、过期 finally 不动 `exporting`。
- 防回归测试两条：导出视图关闭→重开回到打印预览；在途导出被关闭后旧结果不串场、不干扰新一轮导出。
- 纸型（60×40/A4）的 localStorage 记忆是有意设计，不在本次范围。

## Capabilities

### New Capabilities

（无）

### Modified Capabilities

- `fa-layout-and-print`：标签打印弹窗健壮性要求——新增「关闭弹窗复位导出会话」场景。

## Impact

- `frontend/src/views/assets/AssetPrintDialog.vue`：`watch(visible)` 关闭分支、`openExport` 会话序号守卫。
- `frontend/src/tests/views/AssetPrintDialog.test.ts`：新增两条用例。
- 不涉及后端与数据模型。提案审查两问：无信息双存、无台账数量变动，通过。
