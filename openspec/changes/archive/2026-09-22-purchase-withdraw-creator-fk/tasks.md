## 1. 后端模型与迁移

- [x] 1.1 `apps/transfers/models.py`：Transfer 增可空 `created_by` FK（`settings.AUTH_USER_MODEL`，`SET_NULL`，`related_name='created_transfers'`，verbose「创建账号(FK)」），注释写明「身份判定唯一依据；创建人字符串=创建时姓名快照（记录性）」
- [x] 1.2 makemigrations：AddField + RunPython 回填（「创建人」先按 name 后按 phone 唯一命中才填，只处理 `created_by__isnull=True` 幂等；纯 Python 聚合；reverse=noop；打印已回填/跳过统计），SQLite/PG 双端 `migrate` 验证
- [x] 1.3 建单三路径写 `created_by = request.user`：create action（views.py ~167 区域）、导入流单行建单（~953）、导入流分组建单（~979）——`Transfer.build` 后落 FK 再 save

## 2. 后端守卫与序列化

- [x] 2.1 `withdraw` 守卫：`transfer.created_by_id != request.user.id`（含 None）→ 400「仅创建人可撤回自己的单据」；删除姓名比对
- [x] 2.2 `serializers.py` 增 `canWithdraw` SerializerMethodField（purchase 且 待审批 且 `created_by_id == request.user.id`；无请求上下文/未认证默认 False），镜像 `canOperate` 模式；fields 列表收编
- [x] 2.3 报表/导出等「创建人」字符串消费方核对零改动（views.py:594 经办人等）

## 3. 测试

- [x] 3.1 更新 `test_purchase_withdraw.py`：建单 helper 补 `created_by`；新增用例——同名不同账号不可撤回（核心）、`created_by` 为空拒绝、`canWithdraw` 字段输出（创建人 true/他人 false/草稿态 false）
- [x] 3.2 迁移回填测试：唯一命中回填、重名跳过、无匹配跳过
- [x] 3.3 后端 pytest 全量绿（778 过/1 跳/6 xf）；`check_ledger_consistency` 报 2 处差异——**既有本地漂移**（A-a00008，实例生成于 09-17 早于本变更，改动不触碰数量，另行处置）

## 4. 前端

- [x] 4.1 `types/index.ts`：TransferDocument 增 `canWithdraw?: boolean`
- [x] 4.2 `PurchaseDetail.vue`：`canWithdraw(doc)` 改为 `doc.canWithdraw === true`；删除 `currentUserName()` 与姓名比对；确认弹窗/刷新逻辑不变
- [x] 4.3 vitest 全量绿 + `npm run build` 类型门禁通过

## 5. 收尾

- [x] 5.1 拆 feat + openspec 两 commit，push
- [x] 5.2 归档顺序：先归档 `purchase-withdraw-and-excel-ui`（其 ADDED 需求入基线），再归档本变更
- [x] 5.3 生产部署（用户自行 `bash deploy.sh`，migrate 含回填），健康检查（2026-09-22 部署成功，回填 1905 张零跳过）
- [x] 5.4 手验：同名测试账号互看无撤回按钮、创建人撤回全链路、回填统计日志确认（同名场景后端用例覆盖；2026-09-22 线上他人账号确认无撤回按钮）
