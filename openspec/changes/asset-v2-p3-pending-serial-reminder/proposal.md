## Why

P3 第三刀：待补录提醒。实例序列号的"待补录"判定/筛选/补录闭环自 P2 起完备（空串即待补录、`pending_serial=1` 筛选、supplement 补录端点），但全靠用户主动想起去筛——采购入库生成的实例出生即待补录，没人提醒就永远躺在档案里，序列号台账形同虚设。缺的是一条被动获知通道。

## What Changes

- **侧边栏"实例档案"子项徽标**：沿用"资产盘点"动态徽标的既有模式（挂载时拉 count），侧边栏库存组 → 实例档案子项显示待补录实例数；计数走既有实例列表接口（`pending_serial=1&pageSize=1` 取 count），数据范围遵循 DataScope（各人只看自己范围内的待补录）；计数为 0 不显示徽标。子项此前无徽标渲染，模板补一个与顶级徽标同款式的 span。
- 不动后端（判定/筛选/计数能力全部现成）、不建通知（"提醒给谁"在实例场景无明确责任人集合，徽标按浏览者范围展示即正确语义，避免为提醒而扩 notification_type）。

## Capabilities

### New Capabilities
- `pending-serial-reminder`: 待补录序列号的被动提醒通道——侧边栏徽标按浏览者数据范围显示待补录实例数，点击进入实例档案页即可筛选补录。

### Modified Capabilities

（无——`document-instance-binding` 的"序列号待补录"需求（判定/筛选/补录）不变，本变更是其上的提醒层。）

## Impact

- 前端：`components/layout/SidebarNav.vue`（子项徽标渲染 + 待补录计数拉取）、vitest 新增 SidebarNav 徽标用例。
- 后端：零改动。
- 测试：前端 vitest 断言徽标随 count 显隐、计数请求带 `pending_serial=1`。
