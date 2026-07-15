## Why

资产流转模块 4 个列表页（采购入库 / 领用出库 / 调拨 / 回收）每条单子的「操作」列有 **详情 / 通过 / 驳回**（采购另有「提交」）按钮，目前：

1. **距离太近**——按钮直接相邻放在单元格内、彼此无间距，挤成一团；
2. **按钮样式偏弱**——描边细、底色淡，不够醒目、按钮感不强。

应统一加上**合适间距**与**更清晰的按钮样式**。

## What Changes

- **间距**：操作按钮之间加合适间距（`action-buttons.css` 中加 `.action-btn + .action-btn { margin-left }`，纯 CSS、无需改模板、抗 `v-if` 显隐）。
- **按钮样式**：增强 `.action-btn` 系列的按钮感——更醒目的内边距/描边/底色与状态色（详情中性、通过主色、驳回危险色），保留 hover 反馈。
- 改动集中在共享的 `styles/action-buttons.css`（4 个列表页均已 `@import`），一处生效。

## Capabilities

### New Capabilities
- `transfer-list-action-buttons`: 流转 4 个列表页的操作按钮（详情/通过/驳回）具备清晰按钮样式与合适间距。

### Modified Capabilities
<!-- 无：现有 specs 中不含流转列表操作按钮样式 capability。 -->

## Impact

- **前端** `styles/action-buttons.css`（间距 + 按钮样式增强）；4 个列表页操作按钮已统一用 `.action-btn`，无需改模板。
- 无后端、无 DB 迁移。
