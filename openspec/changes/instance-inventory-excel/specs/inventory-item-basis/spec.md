# inventory-item-basis 增量

## ADDED Requirements

### Requirement: 实例盘点 Excel 模板与结果导入

实例盘任务 SHALL 支持下载模板与导入结果（与台账盘点同入口同护栏）：模板 MUST 预填该任务实例清单快照，列为 序号/内部编号/序列号/品目编号/品目名称/使用人/所属部门/核对结果/备注；导入 MUST 仅限 in_progress 任务，按内部编号匹配清单项，核对结果列「已找到」→matched、「未找到」→missing，并记核对人/时间、核对次数 +1；非法结果值或不 在清单的行 MUST 计入行级错误跳过（不中断整表）；文件 MUST 经 Excel 上传校验（扩展名/大小/行数）。导入回写与点选/扫码同口径，不改变漏盘规则与差异处置。

#### Scenario: 下载实例盘模板

- **WHEN** 实例盘任务（清单 3 台）下载模板
- **THEN** Excel 含 3 行快照（内部编号/使用人等预填），核对结果列留空

#### Scenario: 导入回写结果

- **WHEN** 模板填 2 行「已找到」、1 行「未找到」后导入
- **THEN** 对应清单项 result 变为 matched×2、missing×1，核对次数各 +1，返回 imported=3

#### Scenario: 非法值行级报错

- **WHEN** 某行核对结果填「找不到设备」（非法值）
- **THEN** 该行计入 errors 跳过，其余行正常导入

#### Scenario: 非盘点中任务导入被拒

- **WHEN** 对 pending 状态的实例盘任务导入
- **THEN** 返回 400「只有盘点中的任务可以导入」
