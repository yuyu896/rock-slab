# 实例级供应商覆盖 — 技术设计

## Context

batch_update 供应商写 `inst.birth_line.供应商`；generate_instances 使同采购行 N 台实例共享 birth_line（81 台/行实锤）。序列化 get_供应商 现为 `birth_line.供应商 or transfer.供应商`。

## Decisions

### D1：FixedAsset.供应商 可选列（个体覆盖）

`供应商 CharField(200, blank, default='')`，migration additive。get_供应商 三级：`obj.供应商 or (birth_line.供应商 if birth_line) or (birth_line.transfer.供应商) or ''`。铁律一自检：实例存的是**个体覆盖**（"这台机器实际换了供应商"），出生行存**批次口径**（"这批采购的供应商"）——两层语义不同层，非重复存储；无覆盖时派生批次值，与 序列号/规格 同模式。

### D2：batch-update 改写实例字段

供应商分支：`inst.供应商 = supplier; inst.save(update_fields=['供应商','updated_at'])`——不再触碰出生行；无出生行的实例不再跳过（个体字段人人可写）。序列号/备注分支不变。

### D3：存量不回滚

已污染出生行无法区分原值/误改值；照旧参与派生（显示不受影响）。此后所有修改走实例字段，污染面不再扩大。

## Risks / Trade-offs

- [旧污染数据遗留] —— 接受；需要人工修正时用批量维护（此后写实例字段，精确）
- [实例/出生行两层供应商并存] —— 语义分层明确（个体 vs 批次），覆盖优先显式

## Migration Plan

additive migration 随部署；无回填。

## Open Questions

（无）
