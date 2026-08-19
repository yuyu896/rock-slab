## ADDED Requirements

### Requirement: 分公司编号格式规则
系统 SHALL 要求所有分公司编号（`Branch.code`）遵循格式 `{2-4位大写字母}{3位数字}`，正则为 `^[A-Z]{2,4}[0-9]{3}$`。

#### Scenario: 合规编号通过校验
- **WHEN** 用户创建或更新分公司，编号为 `SH001`
- **THEN** 系统接受该编号，正常保存

#### Scenario: 编号含小写字母
- **WHEN** 用户创建分公司，编号为 `sh001`
- **THEN** 系统自动转为大写 `SH001` 后保存

#### Scenario: 编号含空格
- **WHEN** 用户创建分公司，编号为 ` SH001 `
- **THEN** 系统去除首尾空格后保存为 `SH001`

#### Scenario: 编号格式错误
- **WHEN** 用户创建分公司，编号为 `上海001` 或 `SH01` 或 `SH-001`
- **THEN** 系统拒绝并返回错误提示：「编号格式为2-4位大写字母(城市缩写)+3位数字，如 SH001」

### Requirement: 前端实时校验
前端分公司编辑表单的编号输入框 SHALL 提供实时格式校验和自动大写转换。

#### Scenario: 输入自动转大写
- **WHEN** 用户在编号输入框中输入小写字母
- **THEN** 输入值实时转为大写显示

#### Scenario: 格式提示
- **WHEN** 编号输入框获得焦点
- **THEN** 显示 placeholder 提示格式示例，如「如 SH001、BJ002」

#### Scenario: 提交前校验
- **WHEN** 用户提交编号格式不合规的分公司表单
- **THEN** 前端阻止提交并显示格式错误提示

### Requirement: 前端常量定义
前端 SHALL 在 constants 中定义分公司编号格式相关的常量，供多处引用。

#### Scenario: 常量可引用
- **WHEN** 前端代码需要校验分公司编号格式
- **THEN** 可从 `@/constants` 引入 `BRANCH_CODE_PATTERN` 和 `BRANCH_CODE_HINT`
