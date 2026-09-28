## Why

Transfer 表出生（0001_initial）是纯调拨单，采购/领用/归还/回收后来加 action_type 复用，继承了化石命名：`调拨日期`实为五类单据通用的业务日期、`调拨原因`实为通用事由字段、模型 verbose_name 至今叫「调拨记录」。标签层已场景化（界面/模板各叫各的），但库字段名与 API key 名不副实，代码可读性持续付税。用户拍板治理（2026-09-24）。

## What Changes

- **`调拨日期` → `单据日期`**：RenameField 手写迁移（非交互 makemigrations 退化为 Remove+Add 会丢数据——0021 教训）；verbose_name 同步
- **`调拨原因` → `事由`**：RenameField + verbose_name 同步
- **模型 Meta verbose_name「调拨记录」→「流转单记录」**
- **用户可见的一切列标签/表头/界面文案零变化**：导入模板列（采购日期/日期/调拨日期/回收日期）、导出列、界面标签（回收日期等场景化标签）全部保持——旧 Excel 模板兼容性零影响；只改库字段名、API key、代码引用
- API key 变化（`调拨日期`→`单据日期`、`调拨原因`→`事由`）：前后端同仓原子部署吸收

## Capabilities

### New Capabilities
（无——纯命名治理，无行为变化）

### Modified Capabilities
- `transfer-type-templates`：模型字段名引用同步（列标签不变）

## Impact

- 后端（58 处引用）：models/serializers（读写与字段声明）/services（generate_document_number 等）/views（导入 header 键名、导出取值、列表排序 `-调拨日期`、台账 dateFrom 筛选 `调拨日期__gte`）/instances/ledger 引用
- 前端（46 处 + 移动端 4 页）：五类创建页 form/payload key、列表/详情取值、types 定义、移动端表单与审批详情
- 测试：前后端全部含 `调拨日期`/`调拨原因` 的夹具与断言
- 部署：两条 RenameField 迁移（元数据级，保数据）；编号生成（DocumentSequence 按日期分段）语义不变仅引用改名
- 非目标：列标签/模板表头/界面文案；`调拨数量`（明细行列名，无单头字段）；`调出/调入分公司`（调拨专属语义本就正确）
