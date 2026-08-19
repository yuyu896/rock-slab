## 1. 后端：UserSerializer 返回名称

- [x] 1.1 `apps/users/serializers.py` `UserSerializer` 新增 `branch_name`/`region_name`（`SerializerMethodField`，返回 `obj.branch.name`/`obj.region.name`，无则为 `None`），加入 `Meta.fields`
- [x] 1.2 测试：`UserSerializer` 返回 `branch_name`/`region_name` = 名称；未设置时为 `None`（2 用例）

## 2. 前端：个人中心显示名称

- [x] 2.1 `components/layout/UserPanel.vue` 两处 `userInfo.branch` → `userInfo.branchName`（头部分司标签 + 信息区「所属分公司」）；`UserInfo` 接口加 `branchName?`
- [x] 2.2 `layouts/MainLayout.vue` 的 `userInfo` 计算属性补 `branchName: userStore.profile?.branchName`
- [x] 2.3 `types/index.ts` 的 `User` 类型加 `branchName?`/`regionName?`

## 3. 验证

- [x] 3.1 后端 `pytest` 全绿（359 passed）
- [x] 3.2 前端 `vue-tsc --noEmit` 通过（exit 0）
- [ ] 3.3 本地手动验证：个人中心「所属分公司」显示真实名称（非 UUID）
