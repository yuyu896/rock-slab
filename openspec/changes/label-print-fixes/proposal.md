# 标签打印弹窗缺陷修复（label-print-fixes）

## Why

对标签打印功能的代码审查发现一处真实缺陷与两处边界问题：①打印弹窗切换纸型时，缩号逻辑（fitLabelLines）在 Vue DOM 更新前测量——按旧纸型的字号与可用宽判定「不超宽」，切换后长文本行不缩号而被 overflow:hidden 裁断，可能打出残缺标签；②「导出图片」渲染失败时静默弹回打印视图，用户无任何反馈（打印通道 QR 失败反而有占位提示，行为不对称）；③内部编号为空的实例导出时文件名退化为 `标签_.png`，且导出列表以文件名为 key 会冲突。

## What Changes

- **纸型切换缩号时序修复**：`switchPaper` 改为待 `nextTick`（DOM class 已切换）后再执行 `fitLabelLines()`，保证任意纸型、任意切换方向下超宽行都走缩号（下限 2.2mm）而非被裁断。打开弹窗的首次 fit 路径（`renderQrCodes` 内已有 nextTick）不变。
- **导出图片失败可见化**：`openExport` 渲染异常时在导出视图内给出错误提示（不再静默回退），并 `console.error` 保留排查线索；与打印通道 QR 失败的占位提示对齐。
- **空内部编号导出兜底**：`labelFileName` 对空内部编号回退到实例 id 短码（如 `标签_未编号_a1b2c3d4.png`）；导出列表 `:key` 改用实例 id（唯一），消除重名冲突。
- 补防回归测试：切纸型后 fit 时序、导出失败提示、空编号文件名/键。

## Capabilities

### New Capabilities

（无）

### Modified Capabilities

- `fa-layout-and-print`：标签打印弹窗行为修正——「单签内容不越界」「纸型切换与记忆」在切换路径上真实成立（缩号随新纸型几何重算）；「导出标签图片（第二通道）」增加失败反馈与空内部编号兜底两条场景。

## Impact

- `frontend/src/views/assets/AssetPrintDialog.vue`：`switchPaper` 时序、`openExport` 错误处理、`exportItems` 数据结构与 `:key`。
- `frontend/src/utils/labelImage.ts`：`labelFileName` 空编号兜底。
- `frontend/src/tests/views/AssetPrintDialog.test.ts`、`frontend/src/tests/utils/labelImage.test.ts`：新增防回归用例。
- 不涉及后端与数据模型。提案审查两问：无信息双存（纯展示层修复）、无台账数量变动（不经流转单），通过。
