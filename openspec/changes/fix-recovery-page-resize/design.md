## Context

流转类页面（采购、领用、调拨、回收）共享相同的页面结构：统计卡片行 → 筛选栏 → 数据表格 → 分页。所有页面位于 `MainLayout` 的 `.content` 容器内，该容器是 flex 子元素。

当前问题链：
1. `.data-table` 设置了 `min-width: 1400px`，强制表格至少 1400px 宽
2. `.main`（MainLayout 的 flex 子元素）默认 `min-width: auto`，不会被压缩到内容宽度以下
3. 即使 `.transfer-page` 设了 `min-width: 0`，上层的 `.main` 仍然是"保护罩"，阻止了整个宽度链的收缩
4. `.table-container` 的 `overflow-x: auto` 无法生效，因为父级链没有任何一个容器真正限制了宽度

## Goals / Non-Goals

**Goals:**
- 打开 DevTools 面板（视口约 600-900px 宽）时，回收页面内容不溢出，表格可横向滚动
- 统计卡片在窄视口下自动换行（已有部分媒体查询，需确认生效）
- 所有四个流转页面统一修复，保持一致的响应式行为

**Non-Goals:**
- 不涉及移动端适配（移动端有独立的 `MobileLayout`）
- 不改变表格列的显示/隐藏逻辑
- 不引入新的 UI 组件或第三方库

## Decisions

### Decision 1: 在 flex 链上的关键节点添加 `min-width: 0`

需要在两层添加 `min-width: 0`：
- `.main`（MainLayout 的 flex 子元素，row 方向）— 这是真正的瓶颈
- `.transfer-page`（各流转页面自身）— 双重保障

仅修 `.transfer-page` 不够，因为 `.main` 作为外层 flex item 默认 `min-width: auto`，会阻止整个宽度链收缩。

**替代方案**: 在 `.content` 上加 `overflow: hidden`。不采用，因为这会截断弹窗等绝对定位元素。

### Decision 2: 保留表格 `min-width: 1400px`，依赖滚动

表格本身保持 `min-width: 1400px`（保证列的可读性），但通过上述容器约束，让表格在 `.table-container` 内横向滚动，而非撑开整个页面。

### Decision 3: 统一修复所有流转页面

PurchaseList、AssignList、TransferList 与 RecoveryList 共享相同的 CSS 结构和问题，一并修复。

## Risks / Trade-offs

- **横向滚动体验** → 可接受，18 列表格在窄屏下横向滚动是标准做法
- **MainLayout 全局修改** → 在 `.main` 上加 `min-width: 0` 影响所有使用 MainLayout 的页面，但这是正确行为——所有页面在窄视口下都应该收缩而非溢出
