## 1. 权线校验实现

- [x] 1.1 在 `backend/apps/users/views.py` 的 `_validate_in_scope` 中、scope 解析之前加入目标当前岗位权线校验（`MANAGEABLE_ROLES[operator.role]`，admin/本人豁免已在前），不满足抛 `ValidationError` 400，文案含目标岗位展示名
- [x] 1.2 同步更新 `_validate_in_scope` 与 `_get_user_queryset` 中「全部数据=全部用户」的注释为「权线内的任何用户」（含退役岗位归一化 `_RETIRED_ROLE_LINE`）

## 2. 测试

- [x] 2.1 新增越权用例：manager(manage_users+scope.all) PATCH/DELETE admin → 400；manager(本分公司) PATCH 同分公司 director → 400
- [x] 2.2 新增降级攻击用例：manager PATCH director 提交 `role: leader` → 400，目标岗位不变
- [x] 2.3 新增回归用例：manager 改/删权线内 manager/leader → 200/204；admin 改任意岗位 → 200；本人 PATCH 自己 → 200；director 对 admin → 400
- [x] 2.4 跑全量后端测试 `pytest` 确认无回归（867 passed / 5 skipped / 6 xfailed）

## 3. 验证与收尾

- [x] 3.1 动态复现口径复验：`test_all_data_manager_cannot_patch_admin` / `cannot_delete_admin` 即 V1-C 攻击场景重放（同造数：manager + manage_users + 全部数据），断言已从 200/204 变为 400
- [ ] 3.2 手验要点记录（manager 账号在人员管理页编辑/删除入口对高岗位用户的实际表现）

> 手验要点：以 manager+「全部数据」授权账号登录 → 人员管理找到 admin/director 用户 → 编辑改名/停用/删除应得「您没有权限管理『xx』用户」类 400 提示且数据不变；对同分公司 leader 的编辑/删除应正常。
