## Context

盘点快照语义：开始盘点（pending→in_progress）时生成清单——实例盘=分公司（可类目过滤）当前「在用」实例快照（InventoryInstanceItem）；台账盘=范围内台账行。现状 start 先 `_transition`（状态已落库）后生成清单，生成结果无人校验——空清单任务照常进入 in_progress 并触发分公司盘点锁。模板导出直接读清单，导入按内部编号/资产编号匹配清单行。生产事故链：领用审批（06:17）晚于开始盘点（06:03）→ 快照 0 → 空模板 + 导入全拒。

## Goals / Non-Goals

**Goals:**

- 空清单开始即拦（pending 保持），文案点明病因与出路
- 模板自带填写指引（下拉+批注），消灭「没找到/未找到」类手误
- 导入在清单空时给出根因提示

**Non-Goals:**

- 清单重新生成功能（作废重建为既定处置）
- 盘点锁、状态机、快照语义、漏盘规则
- 后端导入值校验放宽（照旧严格）

## Decisions

### D1：start 先探测后转换，空即拒

在 `can_transition` 检查后、`_transition` 前，用与生成同一套 queryset 条件**计数**（实例盘：`FixedAsset.filter(当前状态='在用', branch=task.branch[, item__asset_category=task.category.asset_category])`；台账盘：`AssetStock.filter(branch[, 类目])`）——为 0 返回 400，任务保持 pending（零副作用）。非空走原流程（transition + 生成）。计数与生成条件**同源抽公共函数**防漂移；并发窗口（探测与生成间账面变动）由生成 get_or_create 幂等兜底，极端情况下生成少于探测也无害（清单非空即可盘）。
- 备选：生成后再查、为空回滚状态——状态翻转再回滚留中间态痕迹，不如前置拒绝干净；否决。
- 合法空盘场景（新分公司确无资产）：被拦后按文案指引确认范围即可，空盘本无产出。

### D2：模板指引=数据验证下拉+表头批注，不做示例行

实例盘「核对结果」列（第 8 列）加 `openpyxl.worksheet.datavalidation.DataValidation(type='list', formula1='"已找到,未找到"')`，作用区间覆盖数据行；「核对结果」「备注」表头加 Comment（合法值说明、留空=未盘）。台账盘「实盘数量」表头 Comment（整数、留空=未盘）。示例数据行会进导入解析（`min_row=2` 无法区分），不做。下拉仅 Excel UI 层，粘贴绕过由既有后端值校验兜底（错误信息已含合法值提示）。

### D3：导入 hint 为附加字段，不改动逐行错误

import_result 在返回前判定：`清单 count == 0 且 errors 含「不在盘点范围内」` → 响应加 `hint` 字段（病因+出路文案）；否则不附。前端 `handleImportFile` 读 `result.hint`，有则 ElMessage.warning 追加展示（现有逐行错误 console 保留）。判定条件绑定「空清单」而非任何匹配失败——正常的单行错号不该误报根因。

## Risks / Trade-offs

- [探测与生成间账面变动（先领用后开始/边开始边审批竞态）] → 计数为 0 才拦（有 1 台也放行）；文案已引导「先完成审批再开始」，残余竞态窗秒级、后果仅为清单偏少（盘点本就允许范围内差异）
- [DataValidation 兼容性（WPS/旧 Excel）] → openpyxl 标准 list 校验为 Excel 通用特性；失效退化=无下拉，后端校验兜底
- [hint 文案引发误解（非空任务的普通错行）] → D3 条件绑定空清单，互不干扰

## Migration Plan

纯代码无迁移。部署常规 deploy.sh。手验：空范围任务开始被拦；正常任务开始照常；模板打开见下拉与批注；对历史空清单任务（若还有）导入可见 hint。

## Open Questions

（无——三缺陷口径与文案均经事故复盘拍板。）
