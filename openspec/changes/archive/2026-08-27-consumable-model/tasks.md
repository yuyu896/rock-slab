## 1. 后端：三档与联动

- [x] 1.1 `Category.management_type` choices 增 `consumable`；生成纯 DDL migration
- [x] 1.2 `_line_plan` 领用分支按品目管理方式分流（消耗品 = 在库−N，不进在用；对账同源自动跟随）
- [x] 1.3 预检三处拦截：回收/归还拒消耗品行、领用来源=回收库拒消耗品行；"数量管理品目无需选实例"文案改"非实例管理品目"（预检 + instances 终检）

## 2. 后端：迁移命令

- [x] 2.1 `migrate_consumables`：dry-run 三类清单（可迁/需先归零/实例管理）；--apply 只迁在用=0 且回收库=0 的 B 类数量品目，直改字典属性零台账变动

## 3. 前端

- [x] 3.1 `constants` 增 MANAGEMENT_TYPE_LABELS；`types` 加 'consumable'；替换 ItemPicker/Category/AssetSummary/mobile 两处二元判断
- [x] 3.2 CategoryCreate 三档下拉 + 消耗品语义说明
- [x] 3.3 领用编辑器/创建页：消耗品行提示（耗用发放：领出即消耗、不进在用、不可回收）；领用来源=回收库时的警示文案

## 4. 测试与验证

- [x] 4.1 pytest：联动（消耗品领用在库−N 总量降在用不动、混合单行级分流）、三处预检 400、采购/调拨正常、命令 dry-run/apply/跳过、对账等价
- [x] 4.2 前端 `npm run build` + vitest

## 5. 收尾

- [x] 5.1 v2-revision-draft.md §八 第 8 案 ✅；feat + openspec 两 commit → push → 归档
