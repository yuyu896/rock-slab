## MODIFIED Requirements

### Requirement: 采购经办人预填当前用户

采购入库创建页 SHALL 将「经办人」（Transfer 字段 `经办人`，原 `采购经办人` 重命名）预填为当前登录用户姓名；该字段 MUST 保持可修改、选填语义。提交时若值为空，服务端 SHALL 回填创建人姓名（四类单据统一口径，见 transfer-handler-field 能力）；提交校验 MUST NOT 因此增加必填限制。

#### Scenario: 打开创建页即预填

- **WHEN** 已登录用户打开采购入库创建页
- **THEN** 「经办人」显示该用户姓名，可直接提交

#### Scenario: 预填值可改可清空

- **WHEN** 用户将预填姓名清空或改为他人姓名后提交
- **THEN** 改为他人姓名时按输入保存；清空提交时由服务端回填创建人姓名
