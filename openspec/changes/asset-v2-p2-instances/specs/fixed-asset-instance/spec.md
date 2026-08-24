# fixed-asset-instance Specification（整体重塑）

## REMOVED Requirements

### Requirement: FixedAsset model
**Reason**: 模型重塑为四态实例档案：状态枚举（在库/在用/空闲）改为（在库/在用/回收库/退役）；手抄品目文本列（资产编号/资产类目/资产名称/规格/供应商/单价/购入金额/是否租用/数量）违反铁律 1，由 `item` 外键（→品目字典）与出生明细行派生取代；count() 生成编号的竞态由锁行计数器修复。
**Migration**: 数据迁移完成字段搬迁——item 按存量资产编号解析（未登记者自动创建字典存根）；空闲→回收库；供应商/单价/购入金额折叠入备注；内部编号计数行按存量最大序号初始化。

### Requirement: Quantity sync to Asset
**Reason**: P1 已解耦（signals 已停用），Asset 已冻结只读待退役；实例计数与台账的对齐由 `check_ledger_consistency` 实例不变量执法，不再同步第三份存储。
**Migration**: 无存量动作；对账命令新增实例维度执法。

### Requirement: FixedAsset API
**Reason**: 手动 CRUD 下线——实例出生=采购单（或存量迁移），状态变动=流转单，铁律 2 的实例版。保留 list/retrieve/export，新增序列号补录端点（`manage_instances` 权限）与生平查询。
**Migration**: 前端「新增固定资产」入口移除；写接口返回 405/410 并提示经流转单操作。

### Requirement: Frontend fixed asset page
**Reason**: 列与操作随模型重塑整体重做（详见 fixed-asset-table-columns delta）。
**Migration**: 新列布局与补录弹窗、生平视图随本变更交付。

### Requirement: Excel import for fixed assets
**Reason**: 导入即绕过单据写实例，违反实例层铁律；存量由迁移承载，新增实例走采购单。
**Migration**: 导入端点返回 410；模板下载与导入按钮移除。

## ADDED Requirements

### Requirement: 实例档案模型

FixedAsset MUST 为四态实例档案：字段含 `item`（→品目字典，PROTECT）、`内部编号`（唯一，`{品目编号}-{序号}`，锁行计数器生成）、`序列号`（空=待补录）、`当前状态`（在库/在用/回收库/退役，退役为终态）、`使用人`（记录性文本）、`department`（→部门字典 FK，可空）、`branch`（→分公司 FK）、`birth_line`（→出生采购明细行 FK，可空=存量迁移）、`入库日期`、`备注`。模型 MUST NOT 存放资产编号/名称/规格/类目/供应商/单价等品目文本列——品目信息经 `item` 联字典输出，供应商/单价/采购日期经出生行派生输出（决策 #8）。实例 MUST NOT 被物理删除。

#### Scenario: 品目信息联字典输出

- **WHEN** 客户端请求实例列表
- **THEN** 每行输出品目编号/名称/规格/类目/管理方式（item 联查）与供应商/单价/采购日期（出生行派生），实例表无冗余文本列

#### Scenario: 退役实例档案保留

- **WHEN** 某实例经回收直接处置转入退役态
- **THEN** 该实例记录仍在库中且可查询，MUST NOT 出现任何物理删除路径

### Requirement: 内部编号锁行发号

内部编号 MUST 经实例序列计数行（`InstanceSequence`，品目一行）以 `select_for_update` 锁行自增生成，格式 `{品目编号}-{序号}`；MUST NOT 使用 count() 等存在并发竞ta的方案；唯一约束兜底，并发生成 MUST NOT 重号。

#### Scenario: 连续新增不重号

- **WHEN** 品目 X 已有实例至 X-6，采购单再生成 3 个实例
- **THEN** 新实例为 X-7、X-8、X-9，无重号

### Requirement: 序列号补录端点

系统 MUST 提供实例序列号补录端点（PATCH，仅 序列号/备注 两字段），要求 `manage_instances` 操作码；补录 MUST NOT 触碰状态/使用人/分公司（那些经流转单变动）。无权限 MUST 拒绝。

#### Scenario: 补录序列号

- **WHEN** 持 `manage_instances` 的用户对某待补录实例提交序列号 SN-123
- **THEN** 实例序列号更新为 SN-123，列表待补录标识消失

#### Scenario: 补录试图改状态被拒

- **WHEN** 补录请求携带 当前状态 或 使用人 字段
- **THEN** 返回 400，仅 序列号/备注 可修改

#### Scenario: 无权限补录被拒

- **WHEN** 不持 `manage_instances` 的用户调用补录端点
- **THEN** 返回权限不足错误，实例无变化

### Requirement: 实例生平查询

系统 MUST 提供实例生平查询：输出 = 实例档案 + 出生行派生信息（供应商/单价/采购日期，存量实例为空）+ 关联全部明细行倒序（经行-实例关联反查，含单号/类型/日期/行内记录性字段）。单条明细行 MUST 可反向查看其实例列表。P2 验收标准「任一实例可查完整生平」由本要求落实。

#### Scenario: 查询实例生平

- **WHEN** 用户打开某实例的生平视图
- **THEN** 依时间倒序呈现其出生（采购行信息）与全部流转行（领用/归还/调拨/回收），无缺漏

#### Scenario: 明细行查看实例

- **WHEN** 用户在单据详情明细表点击某行实例列
- **THEN** 展示该行全部实例的内部编号，可跳转实例生平

### Requirement: 实例写接口冻结

除序列号补录外，实例的全部写接口（create/update/partial_update/destroy/batch-delete/导入）MUST 下线并返回 405/410，提示「实例变动请经流转单」。实例状态/使用人/分公司的全部变动 MUST 收敛于 `assets/services/instances.py`（由台账唯一写入口 `ledger.apply_document` 同事务调用）；架构测试 MUST 执法——services/migrations/tests 白名单之外的实例写操作即测试失败。

#### Scenario: 手动创建实例被拒

- **WHEN** 用户 POST /api/fixed-assets/
- **THEN** 返回 405 与「实例出生=采购单」提示

#### Scenario: 架构测试抓到越权实例写

- **WHEN** 某视图代码直接修改 FixedAsset.当前状态
- **THEN** 架构测试失败并指出违规文件
