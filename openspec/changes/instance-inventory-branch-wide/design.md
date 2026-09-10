# 实例盘点去部门维度 — 技术设计

## Context

`InventoryTask.department` 现任三职：① 实例盘判定（`is_instance_inventory = department_id is not None`）② 清单范围过滤（`_generate_instance_items` 按 `department=task.department`）③ 报告展示「盘点部门」。业务口径拍板：实例盘盘全分公司在用实例，部门维度退役。

## Goals / Non-Goals

**Goals:**

- 盘点方式显式化（kind 字段），实例盘范围=全分公司在用实例 × 可选类目
- 存量任务无损迁移（kind 回填、department 保留档案）

**Non-Goals:**

- 台账盘点（stock）行为不变
- 实例盘差异处置口径不变（不自动改账/待跟进/一键回收）
- 存量进行中任务的已生成清单不重算
- department 列不物理删除（历史档案 + 未来若恢复部门维度可复用）

## Decisions

### D1：加 kind 字段而非布尔，is_instance 改读 kind

`kind = CharField(choices=[('stock','台账盘点'),('instance','实例盘点')], default='stock')`。与前端 `INVENTORY_KIND_LABELS`（stock/instance）键名天然对齐，序列化器的派生 `inventory_kind` 改为直读字段。`is_instance_inventory` property 改 `self.kind == 'instance'`——所有调用点（漏盘规则分支、核对端点守卫、报告分支）零改动。

### D2：迁移回填用纯 Python 聚合，同表加列 + 数据回填拆两步

migration 顺序：① AddField（可空，default 不落库——用 `models.CharField(default='stock', null=True)` 先加可空列）② RunPython 回填 `department IS NOT NULL → kind='instance'`，其余 → 'stock' ③ AlterField 改非空。**不用 SQL 聚合、不用 min/max**（SQLite/PG 方差教训），纯 ORM 逐行回填（任务量级千行内）。

### D3：清单生成与创建校验同步收口

- `_generate_instance_items` 删 `department=task.department` 过滤行；select_related('department') 保留（行内仍展示所属部门）
- 创建入参：serializers 移除 department 可写与「部门属于分公司」校验（老任务 department 只读档案）；前端创建页删部门下拉分支
- 报错文案 `该任务不是部门实例盘点` → `该任务不是实例盘点`

### D4：前端 label 与文案

`INVENTORY_KIND_LABELS.instance`：'部门实例盘点'→'实例盘点'；创建页 radio 文案「部门实例盘点（按人逐台核对在用资产）」→「实例盘点（逐台核对全公司在用资产）」；实例盘说明「该部门名下」→「全公司」。列表/详情的 department_name 展示保留（新任务为空、老任务有值）。

## Risks / Trade-offs

- [清单量放大到分公司级（百余台）] → 业务拍板口径；报告按使用人分组维持可操作性
- [存量 rejected/pending 老实例盘任务重开会否按新口径重生成清单] → 开始盘点时生成清单的 get_or_create 幂等：已生成清单的任务不重算，仅新建任务生效新口径——与「不重算存量」目标一致
- [前端仍有部门字段的展示位] → 空值显示为空，无破坏

## Migration Plan

deploy.sh 的 migrate 步骤承载；回滚：kind 列可空兼容旧代码读 department（旧逻辑 `department 非空=实例盘` 对回填后的数据依然成立）。

## Open Questions

（无）
