# ledger-consistency-guard Specification

## Purpose
TBD - created by archiving change asset-v2-p1-contract. Update Purpose after archive.
## Requirements
### Requirement: 对账命令
系统 SHALL 提供 `check_ledger_consistency` 管理命令：对每「分公司 × 品目」行，以单据流水（期初调整单 + 期初时刻之后的已通过流转单 + 全部非期初调整单）重算在库/在用/回收库期望值，与台账存储值逐列比对。全部一致时输出零差异并以退出码 0 结束；任何不一致 MUST 输出差异清单（分公司、品目、列、台账值、期望值）并以退出码 1 结束。

#### Scenario: 全库零差异
- **WHEN** 系统所有数量变动均经唯一写入口，执行 `check_ledger_consistency`
- **THEN** 输出零差异汇总，退出码 0

#### Scenario: 漂移被检出
- **WHEN** 绕过唯一写入口直接篡改某台账行在库数量后执行命令
- **THEN** 输出该行差异明细（台账值 vs 期望值），退出码 1

### Requirement: 唯一写入口与架构测试
台账数量的全部写操作 MUST 收敛于台账服务模块（`assets/services/ledger.py`）。项目 MUST 包含架构测试：扫描 `backend/apps` 源码，断言台账数量写模式仅出现在服务模块、migrations 与 tests 白名单内；违规即测试失败。

#### Scenario: 架构测试抓到越权写
- **WHEN** 某视图代码直接对 AssetStock 数量列执行 F() 更新或 save
- **THEN** 架构测试失败并指出违规文件

### Requirement: 部署检查挂钩
部署脚本（deploy.sh）MUST 在数据库迁移之后执行 `check_ledger_consistency`；命令非零退出时 MUST 中止后续发布步骤并显式告警。

#### Scenario: 部署中对账失败中止
- **WHEN** 部署过程中对账命令退出码 1
- **THEN** 部署中止，不执行后续的流量切换/服务重启完成步骤

### Requirement: 铁律写入项目宪法
`CLAUDE.md` MUST 包含两条铁律原文：一、每样信息只存一处（品目身份在字典、数量在台账、贵重物品档案在实例、变动经过在单据，其余皆为派生）；二、台账数量的每一次变动必须经流转单（含调整单），禁止任何视图/导入/脚本直接改数量。并 MUST 附提案审查两问（是否让某类信息存了两份 / 这次数量变动走单据了吗）。

#### Scenario: 铁律可见于项目说明
- **WHEN** 读取项目根目录 CLAUDE.md
- **THEN** 可见两条铁律与审查两问的完整文本
