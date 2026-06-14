## 1. 后端 — ViewSet 升级与权限控制

- [x] 1.1 `assets/views.py`：AssetViewSet 从 `ReadOnlyModelViewSet` 改为 `ModelViewSet`
- [x] 1.2 `assets/views.py`：实现 `get_permissions()` 按 action 动态设置权限 — update/partial_update/destroy 的 min_role='supervisor'，list/retrieve 保持 min_role='staff'
- [x] 1.3 `assets/views.py`：重写 `perform_update()` — 调用 serializer.save()
- [x] 1.4 `assets/views.py`：重写 `perform_destroy()` — 调用 instance.delete()（硬删除）

## 2. 后端 — Serializer 调整

- [x] 2.1 `assets/serializers.py`：将 `分公司` 和 `分公司编号` 加入 `read_only_fields`，由 serializer 自动从 branch FK 同步
- [x] 2.2 `assets/serializers.py`：重写 `update()` 方法，当 branch 变更时自动填充 `分公司`=branch.name 和 `分公司编号`=branch.code

## 3. 后端 — 测试

- [x] 3.1 测试：supervisor PATCH 自己区域内的资产返回 200
- [x] 3.2 测试：supervisor PATCH 其他区域的资产返回 404
- [x] 3.3 测试：leader PATCH 资产返回 403
- [x] 3.4 测试：supervisor DELETE 自己区域内的资产返回 204
- [x] 3.5 测试：staff DELETE 资产返回 403
- [x] 3.6 测试：修改 branch FK 后 分公司/分公司编号 自动同步

## 4. 前端 — UI 操作

- [x] 4.1 `AssetList.vue`：表格每行增加编辑按钮（supervisor 及以上可见），点击打开编辑抽屉
- [x] 4.2 `AssetList.vue`：表格每行增加删除按钮（supervisor 及以上可见），点击弹出确认对话框
- [x] 4.3 编辑功能：新建 AssetEditDrawer 组件，预填当前资产数据，提交调用 updateAsset API
- [x] 4.4 删除确认：使用 ElMessageBox.confirm 提示"确定删除该资产？此操作不可恢复"
