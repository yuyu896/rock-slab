## 1. 后端模型与迁移

- [x] 1.1 `organizations/models.py`：Department 删 branch FK，唯一约束 (branch,name)→name；docstring 更新为扁平口径
- [x] 1.2 迁移：RunPython 同名合并（保留最早 created_at 行；TransferLine/InventoryTask/FixedAsset 三表 FK bulk 重指向；删除重复行；幂等）→ RemoveField(branch)；纯 Python 聚合；本地 SQLite migrate 验证打印合并统计（406→~8）
- [x] 1.3 `serializers.py` / `views_departments.py`：去 branch 字段/过滤/select_related；选项端点返回全集
- [x] 1.4 `transfers/views.py` 导入 dept_cache（~756）改按 name 单查；grep 全库 `Department.objects.filter` 清点残留调用点逐一核对

## 2. 后端测试

- [x] 2.1 迁移用例：同名合并保留最早行、三表 FK 重指向正确、幂等重跑
- [x] 2.2 接口用例：重名创建 400、选项端点返回全集（无 branch 参数）
- [x] 2.3 后端 pytest 全量绿（重点：组织、流转导入、盘点相关回归）

## 3. 前端

- [x] 3.1 `api/departments.ts`：Department 类型与请求参数去 branch
- [x] 3.2 `DepartmentSelect.vue` 删 branch-id prop；`DepartmentManage.vue` 去分公司列与选择器
- [x] 3.3 领用行编辑器/采购创建/资产表单调用处去过滤参数（grep `branch` 于部门相关组件全量清点）
- [x] 3.4 vitest 全量 + `npm run build` 通过

## 4. 收尾

- [x] 4.1 拆 feat + openspec 两 commit，push
- [x] 4.2 生产部署（migrate 含合并，迁移前备份库），核对合并统计行（2026-09-22 部署成功：kept=8, merged_away=402；台账对账零差异；首次部署踩 PG pending trigger events 已以 atomic=False 修复重上）
- [x] 4.3 手验：部门字典页剩 ~8 条；采购/领用/资产表单部门下拉为全集；历史单据部门名显示不变；新开分公司无需建部门（2026-09-22 用户本地验证通过；新开分公司项待生产确认）
