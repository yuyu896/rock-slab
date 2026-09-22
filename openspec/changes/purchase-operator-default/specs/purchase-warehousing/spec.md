# purchase-warehousing 增量

## ADDED Requirements

### Requirement: 采购经办人预填当前用户

采购入库创建页 SHALL 将「采购经办人」预填为当前登录用户姓名；该字段 MUST 保持可修改、可清空、选填语义，提交校验与后端存储 MUST NOT 因此变更。

#### Scenario: 打开创建页即预填

- **WHEN** 已登录用户打开采购入库创建页
- **THEN** 「采购经办人」显示该用户姓名，可直接提交

#### Scenario: 预填值可改可清空

- **WHEN** 用户将预填姓名清空或改为他人姓名后提交
- **THEN** 单据按用户实际输入保存（空值合法），与现状一致
