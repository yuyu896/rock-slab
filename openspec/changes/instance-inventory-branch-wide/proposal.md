# 实例盘点去部门维度——盘全分公司在用实例

## Why

实例盘点的业务口径本应是「盘整个公司的实例管理物品」，但当前实现以「盘点部门」为实现载体：创建实例盘任务必须选部门，清单只含该部门名下在用实例。部门维度多余（核对按使用人逐台进行，与部门无关），且把「是否实例盘」隐式绑定在 department 字段上（非空即实例盘）是设计债。本次显式化盘点方式并放开范围为全分公司。

## What Changes

- `InventoryTask` 新增 `kind` 字段（stock=台账盘点 / instance=实例盘点，默认 stock），`is_instance_inventory` 改读 kind；存量迁移：department 非空的老任务 → kind=instance（department 值保留作档案，不再参与任何逻辑）
- 实例盘清单生成去掉部门过滤：**全分公司「在用」实例管理物品 × 可选类目**，一台一行
- 创建实例盘任务不再选/传部门；部门必填校验移除；「部门必须属于分公司」校验随入参一并退役
- 前端：创建页去掉盘点部门下拉，label「部门实例盘点」→「实例盘点」，说明文案改为「全公司在用实例」；报告/详情中盘点部门行为空（老任务仍显示）
- 报错文案「该任务不是部门实例盘点」→「该任务不是实例盘点」
- 非目标：台账盘点（stock）行为不变；实例盘差异不自动改账的既有口径不变（报告标记待跟进）；存量进行中任务的已生成清单不重算

## Capabilities

### New Capabilities

（无）

### Modified Capabilities

- `inventory-item-basis`: 盘点方式显式化（kind 字段）+ 实例盘清单口径从「部门名下在用实例」改为「全分公司在用实例」

## Impact

- **后端**: `inventories/models.py`（kind 字段 + is_instance_inventory + migration 含存量回填）、`views.py`（清单生成去部门过滤、创建校验、报错文案）、`serializers.py`（kind 入参）
- **前端**: `constants/index.ts`（label）、`InventoryTaskCreate.vue`（去部门下拉与文案）、列表/详情/报告相关展示
- 数据：存量任务 kind 回填一次性迁移；department 列保留不删
- 风险：实例盘清单量从部门级放大到分公司级（百余台逐台核对），属业务口径拍板结果
