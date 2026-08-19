## ADDED Requirements

### Requirement: Transfer page container constrains width
流转页面容器（`.transfer-page`）SHALL 设置 `min-width: 0`，确保作为 flex 子元素时可以被视口宽度限制，而非被内部表格的 `min-width` 撑开。

#### Scenario: Viewport narrows when DevTools opens
- **WHEN** 用户在浏览器中打开 F12 开发者工具面板，导致视口宽度缩小到约 600-900px
- **THEN** 回收页面（及其他流转页面）的内容区域 SHALL 不超出可视区域，不产生页面级水平溢出

#### Scenario: Normal viewport
- **WHEN** 视口宽度大于等于 1200px
- **THEN** 页面布局 SHALL 与修复前完全一致，无视觉变化

### Requirement: Data table scrolls horizontally in narrow viewport
数据表格（`.data-table`）SHALL 保持 `min-width: 1400px` 以保证列可读性，但其容器（`.table-container`）SHALL 在窄视口下提供横向滚动。

#### Scenario: Table overflow in narrow viewport
- **WHEN** 视口宽度小于表格内容所需宽度
- **THEN** `.table-container` SHALL 显示横向滚动条，用户可以水平滚动查看所有列

#### Scenario: Table fits in wide viewport
- **WHEN** 视口宽度足够容纳所有列
- **THEN** SHALL 不显示横向滚动条

### Requirement: Stats cards responsive in narrow viewport
统计卡片行（`.stats-row`）SHALL 在窄视口下自动换行显示。

#### Scenario: Stats cards at medium viewport
- **WHEN** 视口宽度在 768px 至 1200px 之间
- **THEN** 四张统计卡片 SHALL 以 2×2 网格排列

#### Scenario: Stats cards at narrow viewport
- **WHEN** 视口宽度小于 768px
- **THEN** 四张统计卡片 SHALL 纵向堆叠为单列

### Requirement: All transfer pages have consistent responsive behavior
所有四个流转页面（PurchaseList、AssignList、TransferList、RecoveryList）SHALL 具有一致的响应式布局行为。

#### Scenario: All transfer pages resize correctly
- **WHEN** 用户在任一流转页面（采购、领用、调拨、回收）打开 DevTools
- **THEN** 该页面 SHALL 正确缩窄，表格可横向滚动，无页面级溢出
