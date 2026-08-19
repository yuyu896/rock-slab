## Context

- 4 个流转列表页（`PurchaseList`/`AssignList`/`TransferList`/`RecoveryList`）操作列统一用 `<button class="action-btn">详情</button>` + `class="action-btn approve"`（通过）+ `class="action-btn reject"`（驳回）；采购另有草稿「提交」。
- 按钮直接放在 `<td>` 内，**未**用 `.action-buttons`（flex+gap）容器包裹 → 按钮相邻无间距。
- `.action-btn` 现样式偏弱：`padding:4px 10px`、细描边、淡底色；`.approve`/`.reject`/`.warehouse` 有状态色但为描边式。
- 4 页均 `@import '@/styles/action-buttons.css'`，样式共享。

## Goals / Non-Goals

**Goals:**
- 操作按钮之间有合适间距，不挤在一起。
- 按钮样式清晰醒目、可区分（详情中性 / 通过主色 / 驳回危险色）。

**Non-Goals:**
- 不改操作的功能、权限、显隐逻辑（`v-if` 审批状态等不动）。
- 不动其它模块的按钮。

## Decisions

### 决策 1：间距用相邻兄弟 margin（纯 CSS）
- **做法**：`action-buttons.css` 加 `.action-btn + .action-btn { margin-left: 8px; }`。
- **理由**：无需改 4 处模板；对 `v-if` 显隐稳健（仅相邻可见按钮间产生间距）；4 页均不使用 `.action-buttons` 包裹，无双重间距冲突。
- **备选**：把按钮包进 `<div class="action-buttons">`（用既有 flex gap）——需改 4 处模板，**否**。

### 决策 2：增强按钮样式（更醒目、状态色分明）
- **做法**：适度增大 `.action-btn` 内边距、强化描边/底色；`详情` 中性、`通过(.approve)` 主色更实、`驳回(.reject)` 危险色更实；保留各 hover 反馈。
- **理由**：提升按钮感与可区分度，符合「应当有按钮样式」。

## Risks / Trade-offs

- **[窄列换行]** 操作列较窄时按钮可能换行 → **缓解**：`.action-btn` 已 `white-space: nowrap`，操作列宽度足够。
- **[样式主观]** 醒目程度因人而异 → **缓解**：实现时给出克制、一致的风格，可再按反馈微调。

## Migration Plan

1. 前端：`action-buttons.css` 加间距规则 + 增强按钮样式。
2. 纯前端 CSS，**无 DB 迁移**；部署即生效。

## Open Questions

（暂无。）
