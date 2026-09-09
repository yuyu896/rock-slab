# management-permissions 增量

## ADDED Requirements

### Requirement: 岗位授权批量种子对账

系统 SHALL 提供幂等的批量种子命令（`seed_position_grants`），按以下口径为批量建号后的存量账号补授，默认 dry-run、`--apply` 写入、只补不删：

1. 非 admin 在职用户 SHALL 按岗位模板（`POSITION_TEMPLATES`）补齐缺失操作码，既有特例授权 MUST NOT 被删除；
2. manager/leader 挂有本分公司的 SHALL 补该分公司节点授权；
3. director 的范围 SHALL 来自大区负责人任命（任命即授权），种子 MUST NOT 重复创建节点记录；
4. admin 用户的冗余授权记录 SHALL 清空（运行时恒真，删除零损失）；
5. 无节点授权且无任命覆盖者（如轮空人员）MUST 列人工清单，MUST NOT 自动猜测组织节点。

部署校验命令（`check_seed_grants`）的抽样口径 SHALL 与岗位模板一致，范围预警 SHALL 排除任命已覆盖的用户。

#### Scenario: 分公司行政补码并补节点

- **WHEN** 挂在"杭州一分"的分公司行政（manager）无任何授权记录，批量种子执行 `--apply`
- **THEN** 该用户获得岗位模板全量操作码，并获得"杭州一分"分公司节点授权

#### Scenario: 总监靠任命不建节点

- **WHEN** 某总监（director）已被任命为大区负责人，批量种子执行
- **THEN** 该总监获得岗位模板操作码，且不创建任何 ManagementScope 节点记录（范围来自任命）

#### Scenario: 特例授权保留

- **WHEN** 某用户在种子前持有模板外特例授权（如 view_audit）
- **THEN** 种子后该特例授权仍然存在（只补不删）

#### Scenario: 轮空人员不猜节点

- **WHEN** 某分公司行政未挂任何分公司、也无负责人任命
- **THEN** 种子不为其创建节点授权，将其列入人工处理清单

#### Scenario: admin 冗余授权被清理

- **WHEN** 某账号岗位为 admin 且持有 ManagementScope/OperationGrant 记录
- **THEN** 种子执行后其全部授权记录被清空，功能不受影响（admin 运行时恒真）

#### Scenario: 种子幂等

- **WHEN** 批量种子连续执行两次 `--apply`
- **THEN** 第二次不产生任何新写入，逐人结论为无变化

#### Scenario: 部署校验按模板口径

- **WHEN** 岗位授权按模板种子完成后运行 `check_seed_grants`
- **THEN** manager/director 抽样按岗位模板核对通过，任命已覆盖的用户不出现在范围预警中，校验零错误退出
