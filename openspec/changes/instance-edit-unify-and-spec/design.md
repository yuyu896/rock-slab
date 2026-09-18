# 实例编辑归一 + 规格 — 技术设计

## Context

供应商个体覆盖（instance-level-supplier）已建立三级派生与批量白名单模式；行操作现有 物品图片/补录/生平/打印 四按钮；规格现为 item_spec 两级派生。

## Decisions

### D1：规格复刻供应商模式

`规格 CharField(200, blank, default='')`（migration additive）；`get_item_spec` 三级：`obj.规格 or (birth_line.本批规格) or item.specification`。batch-update 白名单与校验加 规格（与供应商同写法）。

### D2：编辑弹窗整合（替换两个旧入口）

新 `editDialog`（编辑弹窗）：打开时带入行数据——内部编号/品目/使用人/部门（只读上下文，沿用补录弹窗样式）+ 序列号/备注/规格/供应商（可编辑）+ 图片区（当前图预览 + 上传/更换/删除，迁移自 imaging 弹窗）。保存 = 逐项调 batch-update（单台 ids）或直接用既有 supplement（序列号/备注）+ batch-update（规格/供应商）——统一走 batch-update 一次提交（ids=[id]，白名单四项全支持）+ 图片单独走既有 image 端点（上传即时生效）。行操作列变三按钮：编辑/生平/打印。旧 supplementing/imaging 弹窗退役。

### D3：批量菜单五项 + 备注列

batchDialog 类型加 'spec'（输入框弹窗，同 supplier 模板）；列表 thead/tbody 尾部加备注列，colspan 16→17。

## Risks / Trade-offs

- [编辑弹窗一次提交多字段] —— batch-update 白名单本就支持全项，单台提交复用无新风险；图片独立端点即时保存（与表单提交解耦，行为同现状）

## Migration Plan

migration additive 随部署；**完工停本地不部署**（用户本地验证后自行部署）。

## Open Questions

（无）
