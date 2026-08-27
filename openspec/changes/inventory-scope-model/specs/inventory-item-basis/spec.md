## ADDED Requirements

### Requirement: 部门实例盘点
盘点任务 SHALL 支持可选部门维度（`department` FK，须属于任务分公司）：设置部门即为**实例盘**——开始盘点时生成该部门名下 `状态=在用` 实例的快照清单（InventoryInstanceItem，task×instance 唯一），可选类目过滤；核对动作 MUST 逐台进行（found=true→matched / found=false→missing，重复核对以最后一次为准并累计次数），清单 MUST 按部门/使用人分组展示，计数单位为"台"。数量管理品目 MUST NOT 出现实例盘清单（无实例档案层）。台账盘点任务（department 为空）MUST NOT 生成实例清单。重复盘点规则（last/accumulate）MUST NOT 作用于实例盘（一台一勾）。

#### Scenario: 生成部门实例清单
- **WHEN** 分公司 A 部门 D 创建实例盘任务并开始，D 名下在用实例 3 台（品目 X），另有品目 Y（数量管理）库存若干
- **THEN** 清单为 3 行实例项（各含内部编号/使用人），品目 Y 不出现

#### Scenario: 逐台核对
- **WHEN** 盘点人对某在用实例执行核对 found=true，对另一台 found=false
- **THEN** 前者 result=matched（记核对人与时间），后者 result=missing

#### Scenario: 部门不属于分公司被拒
- **WHEN** 创建任务时选择的部门不属于所选分公司
- **THEN** 返回 400 校验错误

### Requirement: 实例盘差异处置（不自动改账 + 待跟进 + 一键回收）
实例盘任务审核通过时 MUST NOT 生成台账调整单（台账与实例状态零变化）；漏盘规则 zero 下提交时未核对实例 MUST 置为 missing（keep 保持 unchecked）。报告 MUST 输出应到/实到/缺失汇总与缺失明细（到内部编号粒度，含使用人/品目），盘亏实例 MUST 标记"待跟进"。报告视图 SHALL 提供对盘亏项发起回收单的入口（预填缺失实例明细跳转回收创建页，走既有审批流）。

#### Scenario: 审批通过不改账
- **WHEN** 实例盘任务含 2 台 missing，审核通过
- **THEN** 任务完成，不生成任何调整单，台账数量与实例状态不变，报告缺失明细含这 2 台（标记待跟进）

#### Scenario: 漏盘归零置缺失
- **WHEN** 实例盘任务漏盘规则=zero，某实例未核对即提交
- **THEN** 该实例 result=missing 进入缺失明细；规则=keep 时保持 unchecked 单列

#### Scenario: 盘亏一键发起回收单
- **WHEN** 操作者在已完成实例盘报告点击"对盘亏项发起回收单"
- **THEN** 跳转回收单创建页且明细行已按缺失实例预填（品目聚合数量+实例），提交后走回收审批流

## MODIFIED Requirements

### Requirement: 盘点明细以台账行为基准

盘点项（InventoryItem）与盘点记录（InventoryCheck）MUST 关联台账行（`stock` FK → AssetStock，分公司×品目），MUST NOT 关联已退役的 Asset。台账盘任务（department 为空）生成明细时 MUST 以任务分公司范围内、选中类目、**目标库别列 > 0** 的台账行为源，应盘数量（expected_qty）MUST 取该任务库别对应列（`stock_bin=stock`→在库数量，`stock_bin=recycle`→回收库数量；默认 stock）。盘点提交（check）MUST 按 stock 定位（asset 编号经 分公司×品目 解析为台账行），未登记品目 MUST 拒绝。

#### Scenario: 生成盘点项来自台账

- **WHEN** 分公司 A 创建盘点任务（库别=在库）并生成明细，台账含 品目 X（在库 5）、品目 Y（在库 0、在用 3）、品目 Z（三列全零）
- **THEN** 生成 品目 X 一项（应盘 5），品目 Y 与 Z 被跳过

#### Scenario: 回收库盘应盘取回收库列
- **WHEN** 分公司 A 创建盘点任务（库别=回收库），台账含 品目 X（在库 5、回收库 2）
- **THEN** 生成 品目 X 一项（应盘 2）

#### Scenario: 按编号提交盘点

- **WHEN** 盘点人提交 编号 X / 实盘 4
- **THEN** 定位到 (任务分公司 × X) 台账行并记录实盘 4，差异留存不动台账

### Requirement: 盘点差异自动生成调整单

台账盘任务（department 为空）审核通过时系统 MUST 在状态机锁内事务中对每个差异项（result 为 surplus 或 missing 且实盘数量非空）经唯一写入口生成调整单：**目标列=任务库别对应列**（stock→在库数量、recycle→回收库数量）、变动量=实盘−应盘（盘盈为正、盘亏为负）、经办人=审批人、来源 MUST 关联盘点任务、事由 MUST 含任务名与前后数量。对应台账列 MUST 随审批同步修正。任一差异调整将致负数时整笔审批 MUST 失败回滚（任务留在 pending_review，台账与调整单零变化，错误信息定位到分公司×品目）。漏盘归零规则（zero）产生的 missing 项 MUST 同样生成调整单；keep 规则下未盘项（unchecked）MUST NOT 生成。无差异项时 MUST NOT 生成任何调整单。**实例盘任务（department 非空）MUST NOT 生成调整单。**

#### Scenario: 审核通过盘亏开单修账

- **WHEN** 台账盘任务（库别=在库）含差异项（应盘 5、实盘 3，台账在库 5）并审核通过
- **THEN** 生成一条调整单（在库 −2，经办人=审批人，来源=该任务），台账在库变 3

#### Scenario: 回收库盘差异修回收库列
- **WHEN** 台账盘任务（库别=回收库）差异项应盘 2、实盘 0，审核通过
- **THEN** 生成调整单（回收库 −2），台账回收库列同步修正，在库列不动

#### Scenario: 盘盈开正量调整单

- **WHEN** 差异项应盘 4、实盘 6，审核通过
- **THEN** 生成调整单（目标列 +2），对应台账列 4→6

#### Scenario: 调整致负数整笔回滚

- **WHEN** 差异项应盘 5、实盘 0，但审批时目标台账列已被流转单扣至 1，审核通过
- **THEN** 审批失败返回 400（定位到该分公司×品目），任务留在 pending_review，台账无变化、不残留调整单

#### Scenario: 漏盘归零生成盘亏单

- **WHEN** 任务漏盘规则=zero，某项应盘 5 未盘，提交后该项记实盘 0/missing，审核通过
- **THEN** 该项生成调整单（目标列 −5）；规则=keep 的任务中未盘项（unchecked）不生成

#### Scenario: 无差异不开单

- **WHEN** 盘点任务全部项 matched，审核通过
- **THEN** 不生成任何调整单，审批正常完成
