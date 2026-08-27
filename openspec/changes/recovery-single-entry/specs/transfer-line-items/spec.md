## MODIFIED Requirements

### Requirement: 单据创建 API 携带明细行数组

五个创建 action（purchase/assign/return/transfer/recovery）MUST 接受 `{...单头字段, items: [...]}` payload：items 非空，每行含品目引用（uuid）、数量与可选 `instances`（实例 uuid 数组，校验矩阵见 document-instance-binding），数量 MUST ≥ 1。领用单 MUST 接受 `领用来源`（stock 默认 / recycle_bin）。品目引用 MUST 指向品目字典已登记品目，未登记 MUST 拒绝并提示相近编号（沿用既有 suggest 机制）；MUST NOT 接受手抄编号字符串创建。类型维度规则沿用既有契约（领用需调出分公司、调拨双分公司且不同、回收需调出分公司）。`draft` 语义保持；`immediate`（行内即时回收）通道已下线（修订 5.1）——回收创建请求携带 `immediate` MUST 被拒绝（400）并引导走回收单审批流，实例退役经审批生效路径按行实例引用执行（不再按文本内部编号物理删除）。

#### Scenario: 多行采购单一次提交

- **WHEN** 用户提交采购单 items 含两个不同品目行
- **THEN** 一次请求创建 1 张单据（含 2 行），返回完整单头与嵌套明细

#### Scenario: items 为空被拒

- **WHEN** 创建请求 items 为空数组或缺省
- **THEN** 返回 400，提示至少需要一条明细行

#### Scenario: 品目未登记被拒

- **WHEN** 某明细行引用的品目 uuid 不存在于字典
- **THEN** 返回 400 并提示品目无效（编号手误场景的相近编号提示由 Excel 导入路径承载，见 transfer-batch-import）

#### Scenario: 领用携带库存来源与实例

- **WHEN** 用户提交领用单 {领用来源: recycle_bin, items: [{item, 数量: 2, instances: [id1, id2]}]}
- **THEN** 创建成功，行关联 2 个回收库实例，待审批
