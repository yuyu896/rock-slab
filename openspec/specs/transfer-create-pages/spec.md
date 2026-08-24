# transfer-create-pages Specification

## Purpose
流转单新建操作以独立路由页面承载，页面由"单头表单 + 明细行表格"构成：品目经字典点选（禁手抄编号），多行单据一次请求提交。

## Requirements
### Requirement: 新增操作以独立路由页面承载
资产流转（采购入库、领用出库、调拨、回收）以及新增固定资产、新增资产的"新建"操作 SHALL 通过独立的路由页面承载，而非模态弹窗。列表页的"新建"按钮 MUST 改为导航到对应的 create 路由，原内嵌模态（`showCreateModal` / `el-dialog` / `modal-overlay`）MUST 移除。

#### Scenario: 列表页"新建"按钮跳转到创建页
- **WHEN** 用户在采购入库/领用出库/调拨/回收列表页点击"新建"按钮
- **THEN** 系统导航到该类型的 create 路由页面（如 `transfers/purchase/create`），不再弹出模态框

#### Scenario: 创建页提交成功后返回列表并刷新
- **WHEN** 用户在创建页填写完毕并提交成功
- **THEN** 系统导航返回对应的列表页，且列表数据被刷新以包含新增记录

#### Scenario: 创建页取消/返回不产生脏数据
- **WHEN** 用户在创建页点击"取消"或浏览器后退
- **THEN** 系统返回列表页，不提交任何数据，列表内容保持不变

### Requirement: 字段与校验与原弹窗一致
新建页面 SHALL 由"单头表单 + 明细行表格"两部分构成：单头表单保持既有字段、必填项与业务校验（调拨创建 MUST 保留"调出分公司与调入分公司不可相同"校验）；明细行表格 MUST 支持增删行，每行以品目字典点选组件选择品目（按编号/名称检索，选中回显规格/类目/管理方式，MUST NOT 手抄编号文本），并按类型展示专属列（采购：单价/金额；领用：使用人/领用部门；回收：存放位置/固定资产内部编号；调拨：本批规格）。领用创建页 MUST 以一次请求提交整张多行单据，MUST NOT 逐行循环发起多张单据。

#### Scenario: 调拨创建阻止相同出入分公司
- **WHEN** 用户在调拨创建页选择相同的调出分公司与调入分公司并提交
- **THEN** 系统阻止提交并提示调出与调入不可相同

#### Scenario: 必填字段缺失阻止提交
- **WHEN** 用户未填写单头必填字段或明细行为空/数量小于 1 即提交
- **THEN** 系统阻止提交并在对应位置提示必填

#### Scenario: 品目必须字典点选
- **WHEN** 用户在明细行选择品目
- **THEN** 通过字典搜索点选完成，选中后行内自动回显名称/规格/单位，不出现自由文本编号输入框

#### Scenario: 多行领用一次提交一张单据
- **WHEN** 用户在领用创建页添加 3 个明细行并提交
- **THEN** 前端发起一次请求创建含 3 行明细的单张领用单

### Requirement: 旧版采购页清退
旧版采购页（`views/Purchase.vue`、`views/purchases/PurchaseCreateForm.vue`、路由 `/assets/purchase`）MUST 移除，访问旧路由 MUST 重定向到 `/transfers/purchase`；其批量导入弹窗能力 MUST 保留在采购列表页。

#### Scenario: 旧采购路由重定向
- **WHEN** 用户访问 `/assets/purchase`
- **THEN** 系统重定向到 `/transfers/purchase`，不出现 404
