## 1. 实现

- [x] 1.1 `backend/apps/users/admin.py`：反注册 User（模块保留说明注释）
- [x] 1.2 `backend/rock_slab/wsgi.py`：setdefault 改 `rock_slab.settings.production`；`backend/manage.py` 加分工注释（缺省维持 development）

## 2. 测试

- [x] 2.1 新增用例：admin 站点注册表不含 User；全量 `pytest` 通过（909 passed / 5 skipped / 6 xfailed）

## 3. 收尾

- [ ] 3.1 手验要点记录（部署后 /admin/ 模型列表无用户）

> 手验要点：部署后以超管开 SSH 隧道访问 /admin/，模型列表应无「用户」；本地 `python manage.py shell` 等命令行为不变。
