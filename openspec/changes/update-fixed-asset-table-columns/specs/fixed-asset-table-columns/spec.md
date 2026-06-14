## ADDED Requirements

### Requirement: 固定资产表展示19列
固定资产表 SHALL 展示固定的 19 列，顺序为：序号、分公司编号、分公司、资产编号、资产类目、物品分类、资产名称、电脑序列号、供应商、入库日期、是否租用、数量、规格、单价、购入金额、出库日期、所属部门、使用人、当前状态。

#### Scenario: 表格表头完整展示
- **WHEN** 用户打开固定资产表页面 `/fixed-assets`
- **THEN** 表头 SHALL 按上述 19 列顺序展示，操作列在最后（有权限时）

#### Scenario: 父级品目字段正确显示
- **WHEN** 表格渲染某条 FixedAsset 实例数据
- **THEN** 序号、资产类目、物品分类、资产名称、是否租用、数量、规格、单价、购入金额、出库日期 SHALL 从该实例关联的父级 Asset 品目读取显示

#### Scenario: 实例字段正确显示
- **WHEN** 表格渲染某条 FixedAsset 实例数据
- **THEN** 分公司、分公司编号、资产编号、电脑序列号（取自实例的序列号字段）、供应商、入库日期、所属部门、使用人、当前状态 SHALL 从 FixedAsset 实例自身读取

### Requirement: 新增表单覆盖实例可编辑字段
新增固定资产弹窗 SHALL 包含 FixedAsset 实例的可编辑字段：资产编号（关联品目）、供应商、入库日期、所属部门、使用人、当前状态。

#### Scenario: 新建实例
- **WHEN** 用户在新增表单填写并提交
- **THEN** 系统 SHALL 创建 FixedAsset 实例，关联到对应 Asset 品目，父级品目字段自动继承显示

#### Scenario: 资产编号关联校验
- **WHEN** 用户提交的资产编号在 Asset 品目中不存在
- **THEN** 系统 SHALL 报错提示，不创建实例

### Requirement: 导出包含19列
固定资产表导出的 Excel SHALL 包含与表格一致的 19 列表头和数据。

#### Scenario: 导出 Excel
- **WHEN** 用户点击导出按钮
- **THEN** 下载的 Excel 文件 SHALL 包含 19 列，父级品目字段从关联 Asset 读取，文件名格式为 `固定资产表_YYYY-MM-DD.xlsx`

### Requirement: 导入模板与解析一致
导入模板 SHALL 包含 19 列表头（与表格一致），12 个只读列的数据区域填充浅灰底色并加批注"此列自动继承，无需填写"。导入解析时按资产编号关联品目，只写入实例字段，父级品目字段只读继承。

#### Scenario: 下载导入模板
- **WHEN** 用户下载固定资产导入模板
- **THEN** 模板 SHALL 包含 19 列表头，首行冻结、加粗、自适应列宽；只读列（序号、分公司编号、分公司、资产类目、物品分类、资产名称、是否租用、数量、规格、单价、购入金额、出库日期）数据区域 SHALL 填充浅灰底色并标注"无需填写"

#### Scenario: 导入实例
- **WHEN** 用户上传填好数据的 Excel
- **THEN** 系统 SHALL 按资产编号查找父级 Asset 品目，创建 FixedAsset 实例并写入电脑序列号（→序列号）、供应商、入库日期、所属部门、使用人、当前状态字段，父级品目字段从关联 Asset 继承

#### Scenario: 导入时品目不存在
- **WHEN** 导入行的资产编号在 Asset 品目中不存在
- **THEN** 系统 SHALL 在导入结果中报错，跳过该行

### Requirement: 列表查询性能
固定资产表列表查询和导出 SHALL 预加载父级 Asset 品目，避免 N+1 查询。

#### Scenario: 列表查询预加载
- **WHEN** 后端查询 FixedAsset 列表
- **THEN** 查询集 SHALL 使用 `select_related('asset')` 预加载父级品目
