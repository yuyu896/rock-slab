# 提案：存量实例状态归一命令（P2 第二刀补丁 · 决断路线 A）

## Why

生产体检发现 672 条存量实例仅 6 条合法四态：「使用中」496（旧 Asset 枚举经导入未校验混入）、「空闲中」168、「维修中」/「已报废」2。非法状态被对账镜像与实例列表筛选静默跳过（按「在用」筛选查不出 496 条），页面功能实际是坏的。用户已确认决断路线 A：15 个挂实例品目维持数量管理、旧档案为历史死档——本命令只归一状态枚举，修展示与筛选。

## What Changes

- `services/instances.py` 新增 `normalize_legacy_status()`（同义映射：使用中/维修中→在用、空闲中/空闲→回收库、已报废→退役；只动 当前状态 一列，分公司/台账/单据不碰；写操作收敛 services 层，架构测试白名单不破）
- 新增 `normalize_instance_status` 管理命令：预览（各非法状态条数与映射目标）/--confirm 执行；幂等

## Capabilities

### New Capabilities
（无）

### Modified Capabilities
- `fixed-asset-instance`: 新增存量状态归一 requirement（同义映射表、预览/确认、只动状态列、幂等）

## Impact

- 后端：`apps/assets/services/instances.py`（+normalize_legacy_status）、新增 `management/commands/normalize_instance_status.py`
- 测试：`tests/test_instance_binding.py` +3（映射/幂等/不动台账）；全量 513 绿
- 运维：生产执行 `normalize_instance_status --confirm` 后实例列表筛选/状态列恢复正常；对账输出不变（数量管理品目不参与镜像）
