## Why

`purchase-withdraw-and-excel-ui` 上线的撤回以**创建人姓名字符串比对**判定权限（后端 `transfer.创建人 != request.user.name`，前端同名比对）：同名员工可互相看到并撤回对方的单据；身份判定建立在展示字段上不可靠。账号 FK 才是权限事实源。

## What Changes

- `Transfer` 新增可空 `created_by` FK（`settings.AUTH_USER_MODEL`，`SET_NULL`）——创建账号身份的唯一判定依据；既有「创建人」字符串字段保留为**创建时姓名快照**（记录性字段，展示/导出用，同 `本批规格`/`使用人` 惯例）
- 迁移回填：按「创建人」字符串对 `User.name` / `User.phone` **唯一命中**才填 FK；同名多条或无命中留空（本地 133 账号无重名，可全量回填；生产迁移同逻辑就地跑）
- 建单三路径一律写 `created_by = request.user`：create action、导入流单行建单、导入流分组建单
- `withdraw` 守卫改为 FK 比对；`created_by` 为空的存量单据**严格拒绝**撤回（宁拒不误放，纠错走审批人驳回的既有通道）
- 序列化器新增 `canWithdraw` 服务端判定字段（purchase 且 待审批 且 created_user==当前用户），前端按钮直接消费，**删除前后端全部姓名比对逻辑**
- 铁律自检：身份（FK）与展示（快照）各司其职、不是同一信息双存；撤回仍只发生在入账前，不触碰台账

## Capabilities

### New Capabilities

（无）

### Modified Capabilities

- `purchase-warehousing`: 「待审批采购单创建人自助撤回」需求的创建人判定由姓名字符串改为账号 FK；新增服务端 `canWithdraw` 判定字段；`created_by` 缺失的存量单据不可撤回

## Impact

- 后端：`apps/transfers/models.py`（+created_by FK）、新增 migration（加列+回填，纯 Python 聚合避免 min(uuid) 类坑）、`views.py`（建单三路径 + withdraw 守卫）、`serializers.py`（canWithdraw）
- 前端：`types/index.ts`（TransferDocument +canWithdraw）、`PurchaseDetail.vue`（按钮判定换 canWithdraw，删 currentUserName 姓名比对）
- 存量数据：迁移自动回填；回填后仍为空的行（重名/无主）撤回按钮不出现、后端拒绝——行为变化仅限这类行
- 归档顺序依赖：须晚于 `purchase-withdraw-and-excel-ui` 归档（其 ADDED 需求先入基线，本变更的 MODIFIED 才有落点）
- 测试：同名不同账号不可撤回（本修复的核心场景）、空 created_by 拒绝、canWithdraw 输出正确性、迁移回填断言
