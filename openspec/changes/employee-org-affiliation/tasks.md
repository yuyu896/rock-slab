## 1. 后端模型与迁移

- [ ] 1.1 `apps/users/models.py`：User 增可空 `region` / `team` FK（related_name 区分），Meta 加 CheckConstraint（branch/team/region 至多一个非空），注释写明"至多一个=单一事实源，区组沿树派生"防误判回摆
- [ ] 1.2 makemigrations 生成迁移（纯加列+约束，无数据迁移；SQLite/PG 双端验证）
- [ ] 1.3 `serializers.py`：fields 增 region/team；serializer 层互斥校验（同时传两个 → 400 带提示）；`get_team_name`/`get_region_name` 派生顺序改为直属节点优先、否则沿 branch 树派生（branch 用户响应不变）

## 2. 后端测试

- [ ] 2.1 API 测试：挂组/挂区/互斥 400/全空合法/派生字段输出/归属不产生范围（resolve_user_scope 断言）
- [ ] 2.2 后端 pytest 全绿（含既有用户接口测试回归）

## 3. 前端

- [ ] 3.1 `types/index.ts` User 增 `region?`/`team?` 及派生字段
- [ ] 3.2 `Organization.vue` 移动弹窗：每层可确认（按钮文案随层变化：移到大区X/移到X组/移到X分公司），选深层清浅层；提交按层级写 region 或 team 或 branch
- [ ] 3.3 员工编辑/新建表单：归属三选一级联（可清空），与移动弹窗同口径
- [ ] 3.4 组织架构页员工表"归属"列按派生 team_name/region_name/branch_name 合并展示（无分公司者不再空白）
- [ ] 3.5 `npm run build` 类型检查通过

## 4. 收尾

- [ ] 4.1 拆 feat + openspec 两 commit，push
- [ ] 4.2 生产部署（跳 5.5 台账对账），健康检查
- [ ] 4.3 验收：移动一位轮空组长挂到其行政组，通讯录/架构页显示正确；存量 134 账号约束满足（branch 外全空）
- [ ] 4.4 存量轮空人员补挂区/组（按人员表，另行批量操作，不在本变更内）
