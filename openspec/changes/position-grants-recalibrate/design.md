## Context

权限口诀「岗位定操作、任命定范围、特例才单独授予」。此前组长模板为空（09-08 曾数据层批量授 12 项全量），director 模板 8 项。09-11 两轮拍板（manager 6 项之后）确定四岗终态：admin 内置全能 / director 10 / leader 8 / manager 6——品目字典与台账调整两权从所有非 admin 岗位模板中移除，仅留 admin 与特例授予。

## Goals / Non-Goals

**Goals:**
- director 模板 8→10（去 dictionary，补 audit/instances/dispose），与生产数据一致
- leader 模板空→8 项，组长从特例授予转模板化；新建组长号预填 8 项
- 门禁 `check_seed_grants` 转绿（director 抽样按新模板）

**Non-Goals:**
- 不动 manager（6 项，第 21 案已定）与 admin
- 不做存量迁移命令：生产数据已先行精确收敛（组长 14×8、区负责人 4×10）
- 不改命令与前端（动态读模板/接口）

## Decisions

| 决定 | 理由 |
|------|------|
| leader 模板化为 8 项而非维持空+特例 | 09-08"组长全量"与 09-11 收敛后组长已成为稳定标准岗（8 项），模板化让新号预填正确、口径唯一事实源在代码 |
| 组长保留 approve_transfer/approve_inventory、去除建号与组织权 | 审批是组长主业；建号/组织变动跨组影响大，上收区负责人（director 持 manage_users/manage_organizations）与 admin |
| dictionary/adjust_ledger 从两岗模板移除 | 品目字典是全司共享字典、台账调整是铁律 2 旁门口——两者收口 admin（特例单独授予仍可） |
| 测试改为集合断言（模板 == 授予集） | 防模板与种子命令漂移 |

## Risks / Trade-offs

- **建号路径变窄**：组长不再能建号，新行政入职责走区负责人/admin——用户拍板接受
- **组长无法再开台账调整单**：分公司导入差异调整仍可走（manage_assets 在组长 8 项内，台账导入二选一通道保留）；纯手工调账需区负责人以上或特例
- 回滚简单：还原两处清单即恢复，无数据迁移
