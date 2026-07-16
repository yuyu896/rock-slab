## 1. 权限数据范围排查与修复

- [ ] 1.1 排查 PermissionAssign.vue 保存操作授权时是否同步创建 ManagementScope
- [ ] 1.2 确认员工看不到的具体模块（组织架构 / 资产 / 流转）
- [ ] 1.3 若需修复：在保存操作授权时自动创建/更新 ManagementScope（按选定分公司/区域）
- [ ] 1.4 测试

## 2. 固定资产表资产名称筛选

- [ ] 2.1 后端 FixedAssetFilterSet 加 `资产名称 = CharFilter(field_name='资产名称')`
- [ ] 2.2 前端 FixedAssetList.vue 加资产名称筛选输入框 + 传参
- [ ] 2.3 测试

## 3. 验证

- [ ] 3.1 pytest + vue-tsc 通过
- [ ] 3.2 本地手动验证
