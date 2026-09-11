## 1. 模板变更

- [x] 1.1 `backend/apps/permissions/positions.py`：`POSITION_TEMPLATES['manager'].operations` 改为 6 项（manage_assets / view_audit / view_all_notifications / view_reports / manage_instances / dispose_assets）
- [x] 1.2 grep 全仓引用 manager 模板 8 项清单的代码/测试/文档，逐一更新（`test_position_permissions` 硬编码清单、三处模板外特例夹具换码、过时注释）

## 2. 测试与验证

- [x] 2.1 新增 `test_manager_template_is_six_codes` 显式断言 6 项目标集合；岗位目录接口断言同步 6 项
- [x] 2.2 后端 pytest 全绿：635 passed / 1 skipped / 6 xfailed
- [x] 2.3 本地 `seed_position_grants --apply` 补齐后 `check_seed_grants` 通过 ✓（生产数据已先行精确收敛，部署新代码后即转绿）

## 3. 收尾

- [x] 3.1 拆两 commit 提交：feat（代码+测试）与 openspec（提案四件套），push
- [x] 3.2 生产部署后复跑 `check_seed_grants` 确认转绿（部署随下次 deploy.sh 或单独执行）
