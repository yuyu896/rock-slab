## Context

四个修订条款（设计书 asset-model-v2.md 2026-08-27 修宪记录）落在流转单创建链路上，涉及 5 个前端文件、4 个后端文件。现状：

- `TransferCreateLayout.vue:37` `.create-page { max-width: 960px; margin: 0 auto; }`，四个新建页共用；`InventoryTaskCreate.vue:124` 640px 限宽 + 单列堆叠。
- `TransferLinesEditor.vue`：采购行单价/金额纯手填无联动（:149-150）；领用行校验仅实例管理行强制使用人（:104），部门下拉"选填"（:154）。
- 后端 `validate_line_items_instances`（services.py:38）只对 assign 实例管理行校验使用人（:72-73）；数量管理行、部门无校验。该函数是表单创建 / 驳回编辑 / Excel 导入三条路径的共用预检口。
- 回收创建页无在用数量展示；审批时 `ledger._apply_delta` 报「在用数量不足：当前 0，需变动 -N」（ledger.py:44-51），用户误读为"无库存"。
- 台账查询 `AssetStockFilterSet` 无品目编号精确过滤（keyword 是四字段 icontains，会误中）。

## Goals / Non-Goals

**Goals:**
- 新建/创建页与列表页同一布局纪律：容器撑满内容区，超宽屏仅限栅格列宽。
- 采购行金额"留空自动、手填优先"，前后端同口径。
- 领用行使用人/部门必填（不分管理方式），前端引导"先选分公司再选部门"，后端三路径（创建/编辑/导入）统一强制。
- 回收错单在创建页拦截（在用数量可见 + 提交预检），审批端报错说人话。

**Non-Goals:**
- 不动调拨权限双边校验（第 3 案）、回收入口收口（第 4 案）、盘点详情页（第 2 案）。
- 不做领用部门跨分公司兜底匹配；部门字典按分公司精确过滤，找不到即报错。
- 回收"已领用仍报在用不足"的真 bug 排查（第 7 案生产排查），本案只修体验缺口。
- 领用来源=回收库的在用展示不做（回收库列语义不同，不在修订范围）。

## Decisions

### D1：限宽移除而非换布局组件
`TransferCreateLayout` 直接删 `max-width: 960px; margin: 0 auto`，保留卡片结构；`.form-grid` 超宽屏限列宽（`repeat(2, minmax(0, 640px))`），明细行表格天然撑满。`InventoryTaskCreate` 同步去限宽，5 个字段从单列堆叠改为两列栅格（任务名称跨两列），与流转新建页观感一致。不复用 TransferCreateLayout 组件——跨功能模块引用 views/transfers/components 反向加深耦合，且盘点页字段结构简单，两处 CSS 各自维护成本更低。

### D2：金额补算收敛在共用预检口，三路径一份逻辑
前端在 `TransferLinesEditor` 的 数量/单价/金额 change 时联动：金额为空且单价非空 → 金额 = 单价 × 数量；金额已手填则不覆盖（清空后视为回到自动）。后端在 `validate_line_items_instances` 内对 purchase 行补算（有单价无金额 → Decimal(单价) × 数量），该函数已被 `_create_action` / `update` / `import_excel` 三处调用，改一处全覆盖。备选（在 serializer 或 _build_lines 补算）要么拿不到 action_type，要么丢掉导入路径，弃。

### D3：领用必填同口校验，导入模板加列承接
后端在 `validate_line_items_instances` 对 assign 全部行强制 `使用人` 非空 + `department` 非空（错误带行号与品目定位，沿用现有 err() 风格）。因导入路径也走此函数，领用导入模板必须同步加"使用人"列（插在领用数量后：分公司、日期、资产编号、领用物品、领用数量、**使用人**、领用部门、用途、备注），"领用部门"列由单纯写入单头文本升级为：文本照写单头 + 按（分公司, 部门名）解析行级 Department 外键（解析失败逐行报错）。前端 `validate()` 同步收紧，部门下拉占位文案随是否已选分公司切换（"请先选择所属分公司" / "请选择部门"）。

### D4：回收预检取数走台账列表接口，前端聚合拦截
`AssetStockFilterSet` 增 `asset_code`（`item__asset_code` 精确）过滤，`getAssetStocks` 透传。`TransferLinesEditor` 在 type=recovery 时按（branchName × 品目）拉取在用数量缓存于组件内 Map：品目点选、行数量变化不重拉，调出分公司切换时整体失效重拉。行内展示"在用 N"，`validate()` 对同品目多行合并计量后超在用的拦截（未知行放行，后端审批终检兜底）。不做后端预检接口——创建时点与审批生效时点之间账会动，前端预检只是体验层，终检仍在 ledger 行锁内（现状不变）。

### D5：报错文案分层业务化
`_apply_delta` 保持通用格式（各列共用），在 `apply_document` 的 recovery 分支捕获 LEDGER_INSUFFICIENT 时改写为业务语言：「回收只能回收『在用』中的资产：当前在用 N，不足扣减 M；请核对物品是否未领用、或调出分公司是否选错」，再经 `_with_line_context` 补行号定位。不在 `_apply_delta` 内按 action 分叉——该函数无单据上下文，且归还/领用共享同列报错。

## Risks / Trade-offs

- [领用导入模板列结构变化，存量模板文件列错位] → 导入逐行报错提示列问题；发布说明注明重新下载模板；模板下载接口与解析同步上线，不出现窗口期不一致。
- [前端在用预检与审批终检之间存在时间窗（他人领用/回收并发）] → 预检仅拦截明显错单，终检仍在 ledger 行锁内，不足即整体回滚（现状语义不变）。
- [金额自动算与手填混用的边界（清空回自动）] → 联动仅在金额为空时写入，手填永不被覆盖；空字符串归一化为 null 再判定。
- [超宽屏列宽上限（640px/列）在中等屏可能不生效] → minmax(0, 640px) 在窄容器退化为可用宽度，无需断点。
