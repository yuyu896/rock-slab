## ADDED Requirements

### Requirement: 分公司编码唯一校验

创建/编辑分公司时，若 `code` 已被**其他**分公司占用，MUST 返回 400 校验错误（提示编码已存在），MUST NOT 触发 500。编辑分公司时保留自身当前 `code` MUST 通过校验。

#### Scenario: 创建已存在 code 的分公司

- **WHEN** 创建分公司，`code` 已被其他分公司占用
- **THEN** 返回 400，提示编码已存在，不创建分公司

#### Scenario: 编辑分公司保留自身 code

- **WHEN** 编辑分公司，`code` 与自身当前 code 相同
- **THEN** 通过校验，正常保存

### Requirement: 分公司 team 数据回填

系统 MUST 提供管理命令，根据员工的 `team` 推断并回填分公司的 `team`，且支持 `--dry-run` 预览（不写库）。回填规则：取该分公司员工 `team` 的众数；无员工或员工均无 `team` 的分公司保持 `null`。

#### Scenario: dry-run 预览回填

- **WHEN** 运行 `assign_branch_team_from_employees --dry-run`
- **THEN** 输出每个分公司将被分配的 team（员工 team 众数），不修改数据库

#### Scenario: 执行回填

- **WHEN** 运行命令（不带 `--dry-run`）
- **THEN** 有众数 team 的分公司被赋值；无员工 / 员工均无 team 的分公司保持 `null`
