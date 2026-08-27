## 1. 后端：checks 接口展示字段与过滤（按人流水数据层）

- [x] 1.1 `InventoryCheckSerializer` 增只读展示字段：`checked_by_name`（checked_by.name）、`asset_code` / `asset_name`（stock.item.*），存量字段不动
- [x] 1.2 `checks` action 增 `checked_by`（UUID，可选）过滤参数，过滤后仍走分页
- [x] 1.3 后端测试：checks 返回展示字段（姓名/编号/名称非 UUID）、checked_by 过滤生效、无记录空页

## 2. 后端：报告导出接口

- [x] 2.1 `InventoryTaskViewSet` 新增 `export-report` action（GET，openpyxl 双 sheet）：「盘点报告」= 基本信息 + 统计 + 调整单清单（单据编号/目标列/变动量/事由/经办人/时间，未完成输出"无（任务未完成）"）；「盘点明细」= 序号/编号/名称/类目/应盘/实盘/差异（带正负号）/结果/盘点人/盘点时间/备注
- [x] 2.2 响应与权限对齐 `download_template`（读路径无操作码 + DataScope 过滤，文件名 `盘点报告_{task.name}.xlsx`）
- [x] 2.3 后端测试：完成任务导出含调整单号、进行中导出快照与"未完成"标注、明细行盘点人/备注如实、范围外任务 404、各状态可导

## 3. 前端：详情页改造（明细表 + 流水 + 死按钮）

- [x] 3.1 `api/inventories.ts` 增 `exportInventoryReport(id)`（blob），`getInventoryChecks` 类型对齐新展示字段
- [x] 3.2 `views/Inventory.vue` 详情视图：`viewTask` 改拉 report 接口一次取全（task/progress/items），进度卡数据源切换不回归
- [x] 3.3 详情页新增「物品明细」卡：朴素表格（编号/名称/应盘/实盘/差异/结果/备注），差异正负着色（沿用报告弹窗口径），容器限高滚动，未开始空态提示
- [x] 3.4 详情页新增「盘点流水」卡：盘点人筛选下拉（全部 + 已载入行聚合去重）+ 朴素表格（时间/盘点人/编号/名称/数量/设备），pageSize=100 翻页，checked_by 服务端过滤，空态提示
- [x] 3.5 删「继续盘点」死按钮（含 btn-primary 样式清理），「导出报告」绑定 `exportInventoryReport` blob 下载（loading 态 + 失败提示，模式照抄 downloadTemplateAction）
- [x] 3.6 `views/MobileScan.vue` 最近记录改用新展示字段（asset_code/asset_name/qty/checked_at/checked_by_name），删除 code/name/result/time 幽灵字段引用

## 4. 验证与收尾

- [x] 4.1 后端 `pytest` 全绿
- [x] 4.2 前端 `npm run build`（类型门禁）+ `npm run test` 全绿
- [x] 4.3 feat + openspec 两个 commit → push → 归档 change，v2-revision-draft.md 第 2 案状态改 ✅
