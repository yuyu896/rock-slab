## Context

三处小改均无数据库迁移，逻辑独立，影响范围清晰：

- **移动员工**：`Organization.vue` 的 `confirmMove()` 在 `!s?.branch` 时直接 warn 并返回（line 174），需去掉此守卫并允许提交空 branch。后端 `User.branch` 已为 nullable FK，无后端改动。
- **实例档案导出**：`backend/apps/assets/views.py` 的 `FA_EXPORT_HEADERS` 有 13 列，`export_excel` 逐行组装时仅取 13 个字段。`FixedAssetSerializer` 已输出 `备注` 和 `management_type`（来自 `item.management_type`，驼峰转换后为 `managementType`）。只需加两列定义与对应数据取值。
- **ItemPicker 管理方式筛选**：后端 `CategoryFilterSet` 已支持 `管理方式` 参数，`getCategories()` API 层也已有该 param 类型定义。`ItemPicker.vue` 仅需新增一个可选 `managementType` prop，在全量字典检索（非台账模式）时透传给 `getCategories`；台账模式下由 `getAssetStocks` 侧过滤（后端若不支持则前端 filter）。同时将搜索框 placeholder 从硬编码字符串改为提示用户按编号或名称搜索（已有逻辑，调整文字即可）。

## Goals / Non-Goals

**Goals:**
- 允许将员工移动到无分公司归属状态（branch 置空）
- 实例档案导出补齐备注与管理方式两列
- ItemPicker 新增管理方式筛选下拉，提示用户编号/名称搜索支持

**Non-Goals:**
- 台账模式 ItemPicker 的管理方式服务端过滤（`getAssetStocks` 接口不在本次改动范围）
- 移动员工弹窗的区域/行政组三级级联 UI 重构
- ItemPicker 多选或多条件组合筛选
- 实例档案导出其他列的调整

## Decisions

**D1：移动员工不再强制必选分公司**

去掉 `confirmMove()` 中 `!s?.branch` 守卫；弹窗分公司选择器加 `clearable`，允许用户主动清空。提交时 `branch` 为空字符串则发送 `{ branch: null }`，与后端 nullable 对齐。

替代方案：在后端加校验拒绝空 branch。否决——系统中确实存在无分公司归属员工，业务需要能用移动操作还原这种状态。

**D2：导出列顺序——备注、管理方式追加在末尾**

备注和管理方式加在现有 13 列之后，列序变为：序号、分公司、内部编号、品目编号、品目名称、规格、序列号、当前状态、使用人、部门、入库日期、供应商、采购日期、**备注、管理方式**。

序列化器字段：`备注` 直接来自 `data['备注']`，管理方式取 `data['managementType']` 再调用 `Category.MANAGEMENT_LABELS.get()` 转中文标签。

**D3：ItemPicker managementType 仅作用于全量字典模式**

台账模式（stockColumn 有值）走 `getAssetStocks`，该接口目前不支持管理方式过滤，本次不动后端。若有 managementType prop，台账模式下前端用 `.filter()` 做客户端过滤，兜底覆盖小数据集场景。全量字典模式直接透传 `管理方式` 给 `getCategories`，由后端 `CategoryFilterSet` 处理。

**D4：placeholder 文字统一**

现有硬编码 `'输入编号或名称检索品目'` 已表达意图，当 disabled 时显示"请先选择分公司"。保持现有逻辑，仅将 prop.placeholder 缺省值改为 `'支持按编号或名称搜索'`，更简洁，与产品侧建议一致。

## Risks / Trade-offs

- **[导出列数增加]** 现有已下载的导出模板/宏若写死 13 列索引，会错位 → 此为 Excel 下载文件，无在线宏依赖，风险极低。
- **[branch 置空]** 员工移动后无分公司归属，部分依赖 branch 过滤的查询将不再命中该员工 → 这是刻意行为，管理员可在集团根节点看到这类员工（已有 spec）。

## Migration Plan

三处改动均不涉及数据库迁移，前后端独立发布均可。部署顺序无要求。
