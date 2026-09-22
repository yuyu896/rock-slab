## Why

生产实测（2026-09-21 只读核查）：72 家分公司 410 个部门，其中 **406 条是 6 个部门名 ×~68 家的克隆复制品**（仓库/人事部/行政部/财务部/业务部/渠道），真正分公司特有的仅 4 条（总经办×3、企业文化部×1）。各分公司部门实际一致，按分公司维护字典无业务意义，且每开新分公司需手工克隆 6 个部门。

## What Changes

- `Department` 模型**去掉 branch 外键**，改为全集团扁平字典，`部门名称` 全局唯一
- 迁移：同名部门**合并为一条**（保留最早创建的行），三个 FK 引用表**重指向**合并后行——`TransferLine.department`（领用行部门）、`InventoryTask.department`（盘点任务）、`FixedAsset.department`（实例档案）
- 部门接口与前端下拉**去掉分公司过滤**：选项端点返回全集；`DepartmentSelect` 去 branch-id 参数；DepartmentManage 页去分公司列/选择器
- 流转导入流的部门解析缓存改为按名称单查

## Capabilities

### New Capabilities

（无）

### Modified Capabilities

- `department-dictionary`: 「部门字典模型」「管理与选项接口」「表单部门输入接字典」三个需求按扁平口径修订（存量归一迁移需求为历史记录，不动）

## Impact

- 后端：`organizations/models.py`（Department 删 branch FK + 唯一约束改 name 单列）、迁移（AddConstraint/RemoveField + RunPython 同名合并与 FK 重指向）、`serializers.py`（去 branch 校验/字段）、`views_departments.py`（去 select_related(branch)、去 branch 过滤）、`transfers/views.py` 导入 dept_cache（~756）改按名查
- 前端：`api/departments.ts`（接口参数与 Department 类型去 branch）、`DepartmentSelect.vue`（去 branch-id prop）、`DepartmentManage.vue`（去分公司维度）、领用行编辑器与采购/资产表单调用处（去过滤参数）
- **零影响区（防误伤核心）**：部门不参与组织树与数据范围推导（resolve_user_scope / DataScopeMixin / 任命授权体系不读部门——已核实）；历史单据的部门**名称展示不变**（合并只动 FK 指向，名称未变）
- 生产迁移在 deploy 流程内（迁移前惯例备份）；管理命令 prod_data_fix_20260914 含 branch 过滤的历史脚本不常驻不修
