## Context

Department 定位是归属标签（docstring 明示不参与组织树/数据范围），branch 维度是 P1 设计时"各部门可能不同"的假设，实际业务证伪。FK 消费方三处：TransferLine.department、InventoryTask.department、FixedAsset.department（均已核实，无第四处）。查询点：组织序列化器按 (branch,name) 去重校验、部门视图 select_related(branch)、流转导入 dept_cache 按 branch+name 缓存。

## Goals / Non-Goals

**Goals:** 部门字典全集团一套（~8 条）；历史 FK 引用无缝重指向；表单下拉去分公司过滤。

**Non-Goals:** 不动组织树（Region/Branch/Team）；不动数据范围与权限；不迁移历史单据上的部门**文本**字段（调出/调入/需求部门等快照文本原样）；不借机做部门 FK 化扩展。

## Decisions

| 决定 | 理由 |
|------|------|
| 删 branch FK（而非置空保留） | 字典语义彻底扁平，防止"半扁平"歧义；字段删除是显式断舍离，序列化器/表单同步收口 |
| 同名合并保留**最早创建**的行 | 确定性强（不依赖名称排序歧义）；三条 FK 表 bulk update 指向保留行后删重复行 |
| 迁移顺序：先加 name 全局唯一约束校验→RunPython 合并+重指向→删 branch 字段 | 保证每步可独立验证；纯 Python 循环聚合（SQLite/PG 双端一致，规避 SQL 方言与 min(uuid) 类坑） |
| 选项端点返回全集（不再按 branch 过滤） | 字典=全集 8 条，无需过滤参数；调用方传 branch 参数的兼容期不做（前端同变更一起改） |
| 导入 dept_cache 改按 name 单查 | 分公司语义消失后 (branch,name) 键退化为 name |

## Risks / Trade-offs

- [生产重名部门里混有"同分公司特化"语义] → 数据实测仅 总经办×3/企业文化部×1 特有，合并后仍以独立名称存在于全集，分公司视角下拉多出可选项但无强制；用户已知悉接受
- [迁移期间新增部门并发] → deploy 窗口内低并发；RunPython 幂等（重复执行按 name 已唯一跳过）
- [前端调用方漏改] → 以 grep `branch` 于 departments API/组件全量清点（tasks 1.4），vitest+build 兜底；DepartmentSelect prop 设为可选并忽略亦可平滑，但选择**显式删除** prop 由 TS 编译期抓漏
- [InventoryTask 历史任务部门指向] → 合并重指向后任务详情显示部门名不变，回溯无损
- 回归面：后端 pytest 全量（组织/流转/盘点相关用例）+ 迁移双库验证 + 前端 vitest/build
