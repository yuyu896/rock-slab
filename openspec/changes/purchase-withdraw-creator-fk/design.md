## Context

- 撤回权限现状：后端 `transfer.创建人 != (request.user.name or request.user.phone)`（views.py:333），前端 `doc.创建人 === profile.name`（PurchaseDetail.vue canWithdraw）——两端都建立在展示用字符串上，同名员工互相可见并可撤回对方单据
- `Transfer.创建人` 是 CharField，建单时由后端写 `request.user.name or phone`；导入流写 importer 姓名
- 全项目业务模型**尚无任何 User FK 先例**（grep 仅 users app 自身）——本变更是第一个，需立惯例
- 序列化器已有 `canOperate`（服务端按请求上下文算布尔给前端）的成熟模式可镜像
- 本地 133 账号无重名；生产 134 账号由迁移同逻辑就地回填
- 归属依赖：`purchase-withdraw-and-excel-ui` 尚未归档，其「待审批采购单创建人自助撤回」ADDED 需求还未入基线 specs——本变更的 MODIFIED 增量以其归档为前提

## Goals / Non-Goals

**Goals:**

- 撤回权限判定基于账号身份（`created_by` FK），同名不再互窜
- 前端彻底删除身份比对逻辑，按钮显隐消费服务端下发的 `canWithdraw`
- 存量单据自动回填；回填不了的（重名/无主）明确拒绝撤回

**Non-Goals:**

- 不给其他动作（submit/resubmit/edit/删除）加创建人限制——维持既有权限口径
- 不动「创建人」字符串字段的展示/导出用途（报表「经办人」等消费方照旧）
- 不做全库 User FK 化——只加本变更需要的这一个

## Decisions

| 决定 | 理由（含备选） |
|------|------|
| `created_by` FK 用 `SET_NULL`（vs PROTECT） | 单据是事实记录，账号注销/清理不应被历史单据卡死；身份置空后撤回自然拒绝，展示不受影响（「创建人」快照仍在）。首个业务模型 User FK 立惯例：`related_name='created_transfers'`，verbose「创建账号(FK)」 |
| 「创建人」字符串保留为记录性快照（vs 删除改派生） | FK=身份（权限判定），字符串=创建时姓名（留档展示）——分工明确不是双存；删字段要动报表/导出/前端一堆消费方，收益为零。同 `本批规格`/`使用人` 记录性字段惯例 |
| 回填策略：`创建人` 先按 `User.name` 精确匹配、无果再按 `phone`；**唯一命中才填** | 宁缺勿错——回填错人比留空更糟（错误授权）。空=拒绝撤回，兜底通道（审批人驳回）仍在。纯 Python 循环聚合，规避 SQL 聚合在 SQLite/PG 的方言坑 |
| 空 `created_by` 严格拒绝撤回（vs 姓名比对兜底） | 兜底=漏洞续命，违背本变更目的。行为变化仅限回填失败的行：从「匹配姓名者可撤」变为「无人可撤」 |
| `canWithdraw` 服务端算（vs 前端比 created_by id） | 判定逻辑单点维护（前后端天然一致），前端零身份逻辑；镜像 `canOperate` 模式（SerializerMethodField + context request.user，离线序列化默认 False）。字段名 camelCase 直接落 JSON |
| 迁移：AddField + RunPython 同文件，回填只处理 `created_by__isnull=True`（幂等） | 加列可空无默认，双库安全；回填幂等可重跑；reverse=noop（列保留无害） |

## Risks / Trade-offs

- [生产存在重名账号 → 部分行回填失败] → 迁移打印「已回填/跳过」统计；空行拒撤属预期，必要时 shell 手工指定补挂
- [归档顺序依赖] → 须先归档 `purchase-withdraw-and-excel-ui`（ADDED 入基线），本变更 MODIFIED 才有落点；见 tasks 4.x
- [旧前端仍按姓名比对渲染按钮] → `canWithdraw` 为增量字段；后端守卫已严格，旧前端最多个别该显示的没显示，无越权风险
- [既有测试直建 Transfer 未设 created_by → 撤回用例失败] → 更新 `test_purchase_withdraw.py` 建单处补 `created_by`
