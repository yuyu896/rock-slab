## 1. 修复创建分公司 500（code unique）

- [x] 1.1 `BranchSerializer.validate_code` 增加 unique 校验：编辑时 `exclude(pk=self.instance.pk)`，重复 `raise serializers.ValidationError`（中文「分公司编码 X 已存在」）
- [x] 1.2 后端测试：创建重复 code 返回 400；编辑分公司保留自身 code 通过

## 2. 分公司 team 回填命令

- [x] 2.1 新增 `organizations/management/commands/assign_branch_team_from_employees.py`：按员工 team 众数回填分公司 team，支持 `--dry-run`
- [x] 2.2 命令测试：`--dry-run` 不写库；执行后有众数的分公司 team 正确；无员工/员工均无 team 的分公司保持 null

## 3. 修复错误显示乱码

- [x] 3.1 `handleApiError`（`utils/request.ts`）：`response.data` 为 string/非对象时返回「服务器错误（HTTP {status}），请稍后重试或联系管理员」
- [x] 3.2 前端测试：string 响应返回可读提示；DRF JSON 错误仍正常提取（不回归）

## 4. 验证与部署

- [x] 4.1 后端 `pytest`（395 passed, 6 xfailed）
- [x] 4.2 前端 `npm run build` + `npm run test`（24 passed）
- [ ] 4.3 部署 `deploy.sh`（后端 rebuild + 前端 build，无新 migrate）
- [ ] 4.4 上线后执行 `python manage.py assign_branch_team_from_employees --dry-run` 预览，确认后执行回填
- [ ] 4.5 线上验证：创建重复 code 返回可读 400、回填后未分组员工回到正确行政组、错误提示无乱码
