## Why

调拨单上「调出负责人」与「经办人」语义重复（经办人统一口径刚上线，创建页两字段并排）；批量导入模板携带「调出负责人」列徒增填写负担（采购入库口径=经办人由系统兜底操作人）；「调入负责人」为自由手填，选完调入分公司后应直接下拉选该公司员工（员工都有系统账号，数据现成）。

## What Changes

- **调出负责人退役**：Transfer 字段 `调出负责人` 删除（RemoveField）；存量值先合并进 `经办人`（经办人为空才取调出负责人值，DML 数据迁移与 DDL 删列分离执行，规避 PG 同表混排风险）
- **五处消费面同步收口**：创建页（TransferCreate）删输入框、详情页（TransferDetail extra 区）删展示、导出删列、导入模板删列（后端 TYPE_TEMPLATES + 前端 importTemplate.ts）、导入解析删列——导入路径补 `经办人=导入操作人`（对齐采购口径 `views.py:838` 模式；调拨导入直拼 header 不走 `_create_action`，现有导入单经办人为空）
- **调入负责人下拉化**：调拨创建页选完调入分公司后，调入负责人从手填输入变**纯下拉**（选该公司员工，`GET /api/users?branch=<id>`，users list 已对全体登录用户放开，零后端权限改动）；存姓名文本快照（同领用「使用人」模式，不引 FK）；切换调入分公司时清空已选值
- **旧模板不兼容明示接受**：表头守卫严格匹配，删列后已下载的旧调拨模板再导入将 400，用户拍板不管（重新下载模板即可）

## Capabilities

### New Capabilities
- `transfer-responsible-persons`：调拨负责人治理——调出负责人并入经办人退役（含存量迁移口径）、调入负责人按调入分公司员工纯下拉

### Modified Capabilities
- `transfer-handler-field`：经办人服务端默认的覆盖面从 `_create_action`（表单/移动端/API）扩展到批量导入路径（调拨导入经办人=操作人）
- `transfer-type-templates`：调拨导入模板列删除「调出负责人」，导入映射同步

## Impact

- 后端：`models.py`（RemoveField）+ 两条迁移（数据合并 DML / 删列 DDL 分离）；`serializers.py` 读写字段删除；`views.py` 导出列、TYPE_TEMPLATES 表头、导入解析；收口 grep `调出负责人` 归零（migrations 历史除外）
- 前端：`TransferCreate.vue`（删调出负责人、调入负责人下拉+分公司联动清空）、`TransferDetail.vue`（删调出负责人展示）、`importTemplate.ts`（TRANSFER_HEADERS 删列）；MobileTransfer 无负责人字段不受影响
- 存量数据：调拨单已填的调出负责人值无损并入经办人；非调拨单不受影响（该字段仅调拨场景使用）
- 部署：migrate 含数据迁移+删列，须按分离顺序执行；回滚依赖部署前备份
