# 实例盘点去部门维度 — 实施任务

## 1. 后端模型与迁移

- [x] 1.1 `InventoryTask` 加 `kind`（stock/instance，默认 stock）：三步迁移（加可空列 → RunPython 纯 ORM 回填 department 非空→instance 其余→stock → 改非空）
- [x] 1.2 `is_instance_inventory` 改读 kind；serializers 的 `inventory_kind` 派生改直读字段，移除 department 可写与「部门属于分公司」校验

## 2. 清单生成与端点

- [x] 2.1 `_generate_instance_items` 删 `department=task.department` 过滤（全分公司在用实例 × 可选类目），行内所属部门展示保留
- [x] 2.2 核对端点报错文案「该任务不是部门实例盘点」→「该任务不是实例盘点」；创建入参不再收 department
- [x] 2.3 后端测试：新任务 kind=instance 全公司清单（跨部门实例齐入清单）；创建不传 department 成功；存量回填迁移测试（老 department 任务 kind=instance 且清单不变）

## 3. 前端

- [x] 3.1 `constants`：INVENTORY_KIND_LABELS.instance → '实例盘点'；创建页 radio 文案与实例盘说明更新（全公司在用实例口径）
- [x] 3.2 `InventoryTaskCreate.vue` 删盘点部门下拉与 departmentId 逻辑；提交不带 department
- [x] 3.3 列表/详情/报告的部门字段展示核对（新任务为空不破版，老任务仍显示）
- [x] 3.4 vitest：创建页无部门下拉、提交 payload 不含 department、kind=instance

## 4. 验证与收尾

- [x] 4.1 后端全量 pytest 通过；前端 `npm run build` + vitest 全绿
- [x] 4.2 本地浏览器手验：创建实例盘任务（无部门选择）→ 开始 → 清单为全公司在用实例（跨部门）→ 逐台核对 → 提交报告正常
