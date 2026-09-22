## Why

采购经办人通常就是建单人；现创建页该字段为空、选填、自由文本，每次都要手敲一遍自己的名字。后端字段语义无需变动，纯表单预填即可消除重复输入。

## What Changes

- PC 采购创建页「采购经办人」初始值预填为**当前登录人姓名**（`userStore.profile.name`）
- 字段仍可修改、可清空，选填语义不变；提交链路与校验零变化

## Capabilities

### New Capabilities

（无）

### Modified Capabilities

- `purchase-warehousing`: 新增「采购经办人预填当前用户」需求（ADDED，不改既有需求）

## Impact

- 前端：`views/transfers/PurchaseCreate.vue` 一处初始值（+userStore 引入）
- 不动：后端（字段仍为选填自由文本）、编辑表单（沿单上现值）、移动端提交页（无此字段，已核实）
- 防误伤边界：单文件单字段默认值，无状态机/接口/校验参与
