# 行级供应商 + 批量操作 — 技术设计

## Context

单头供应商唯一；TransferLine 已有记录性字段先例（本批规格/单价）；实例供应商现取出生行 transfer.供应商；实例勾选框架已有（check-col/selectedIds）。

## Decisions

### D1：TransferLine.供应商 可选列 + 派生链

模型加 `供应商 CharField(200, blank, default='')`（migration additive）。序列化：TransferLineInputSerializer 加可选字段（仅 purchase 行消费，其他类型忽略即拒？——宽松：保存任意行但不语义化；**收口：仅 purchase 行允许**，validate_line_items 里非采购行携带即拒，对齐实例矩阵风格）。实例派生 `get_供应商 = birth_line.供应商 or birth_line.transfer.供应商`。导入：采购分支 line_kwargs 加 `'供应商': _cell(row, '供应商')`（列已存在，零模板变更）。

### D2：batch-update 端点（白名单窄口）

`required_operations = {'batch_update': 'manage_instances'}`。入参：`ids: []`, `供应商: str?`, `备注: str?`, `序列号列表: []?`（与 ids 等长才生效）。逻辑：拒绝未知字段；逐台处理收集 results/errors。供应商走 `birth_line.供应商 = v; birth_line.save(update_fields=[...])`（出生行是单据行的记录性列，属档案维护口径——**架构测试注意**：TransferLine 更新不在实例写守卫范围（守卫只盯 FixedAsset 字段赋值），合规）。序列号直写实例（同 supplement 口径，逐台唯一校验）。

### D3：前端批量操作菜单

FixedAssetList：勾选后按钮变「批量操作 ▾」（原生下拉，朴素风格），四项分别：打印（现 printSelected 迁入）、供应商（输入框弹窗）、备注（输入框弹窗）、序列号（列表式逐台输入弹窗：每台一行 input，支持扫码自动跳下一行）。均调 batch-update 后局部刷新。

## Risks / Trade-offs

- [批量改出生行供应商影响单据展示] —— 采购详情行表将显示行级值（变更预期：档案修正语义）
- [序列号批量扫码交互复杂度] —— 逐台行输入+回车跳行，简单可控

## Migration Plan

迁移 additive；随部署生效；存量行供应商空→自动回退单头（零回填）。

## Open Questions

（无）
