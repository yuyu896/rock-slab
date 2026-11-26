## ADDED Requirements

### Requirement: Excel 模板包含内部编号列
领用单批量导入模板 SHALL 包含「内部编号」列，位于第 4 列（资产编号之后、领用数量之前）。

#### Scenario: 数量管理品目导入时编号列留空
- **WHEN** 用户导入数量管理品目（如办公椅）的领用行
- **THEN** 内部编号列 SHALL 留空，数量列正常填写

#### Scenario: 实例管理品目导入时编号列必填
- **WHEN** 用户导入实例管理品目（如电脑）的领用行
- **THEN** 内部编号列 SHALL 填写一个编号，数量列 SHALL 为 1

#### Scenario: 旧版领用模板继续支持数量管理品目
- **WHEN** 用户使用不含「内部编号」列的旧版领用模板导入数量管理品目
- **THEN** 系统 SHALL 按原有数量列导入该行

### Requirement: 实例管理品目行数量固定为 1
实例管理品目的批量导入行 SHALL 要求数量为 1，一行对应一台设备。

#### Scenario: 实例管理品目行数量不为 1 时拒绝
- **WHEN** 实例管理品目的导入行数量 ≠ 1
- **THEN** 系统 SHALL 拒绝该行并提示「实例管理品目每行数量必须为 1」

#### Scenario: 批量领用 3 台电脑时分 3 行
- **WHEN** 用户需要领用 3 台电脑（HZ001、HZ002、HZ003）给张三
- **THEN** 用户 SHALL 填写 3 行，每行内部编号不同、数量均为 1

### Requirement: 按内部编号查询实例
导入解析时 SHALL 按填写的内部编号在分公司内查询实例，并绑定到单据行的 `instances` 字段。

#### Scenario: 编号在分公司内不存在时拒绝
- **WHEN** 导入行的内部编号在指定分公司内不存在
- **THEN** 系统 SHALL 拒绝该行并提示「编号 {编号} 在 {分公司} 不存在」

#### Scenario: 编号对应的品目不匹配时拒绝
- **WHEN** 编号对应的实例品目与导入行的资产编号不一致
- **THEN** 系统 SHALL 拒绝该行并提示「编号 {编号} 品目不符」

#### Scenario: 编号对应的实例状态不符合要求时拒绝
- **WHEN** 编号对应的实例状态不是「在库」
- **THEN** 系统 SHALL 拒绝该行并提示「编号 {编号} 状态 {当前状态} 不符合要求」

### Requirement: 同批次编号唯一性校验
同一批次导入中 SHALL 禁止同一内部编号出现在多行。

#### Scenario: 同批次重复编号时拒绝
- **WHEN** 同一批次导入中编号 HZ001 出现在第 2 行和第 5 行
- **THEN** 系统 SHALL 拒绝第 5 行并提示「编号 HZ001 与第 2 行重复引用」

### Requirement: 复用现有校验逻辑
实例查询后的所有校验（状态、品目、分公司、单据占用）SHALL 由现有 `validate_line_items_instances` 完成，导入逻辑不重复实现。

#### Scenario: 编号被待审批单占用时拒绝
- **WHEN** 编号对应的实例已被其他待审批或草稿单占用
- **THEN** 系统 SHALL 通过 `validate_line_items_instances` 拒绝并提示占用单据信息

#### Scenario: 实例管理品目未填编号时拒绝
- **WHEN** 实例管理品目导入行的内部编号列为空
- **THEN** 系统 SHALL 通过 `validate_line_items_instances` 拒绝并提示「实例管理品目必须选择与数量等长的实例」

### Requirement: 实例管理品目导入权限
导入实例管理品目 SHALL 要求操作者具有 `view_instances` 权限，并 SHALL 在缺少权限时拒绝整个导入请求。

#### Scenario: 操作者没有查看实例档案权限
- **WHEN** 操作者导入包含实例管理品目的行且没有 `view_instances` 权限
- **THEN** 系统 SHALL 返回权限拒绝，且不创建单据
