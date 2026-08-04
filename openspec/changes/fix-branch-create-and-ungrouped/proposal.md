## Why

unified-organization-page 上线后暴露三个相互关联的问题：

1. **创建分公司报 500（前端因 HTML 错误页显示为"乱码"）**：`BranchSerializer` 的 `extra_kwargs={'code':{'validators':[]}}` 本意是禁用 model 自带的 regex 校验（改用 `validate_code`），却把 DRF 自动加的 `UniqueValidator` 一并清空——于是 `code` 重复（如重建原有分公司 `BJ001`）漏过 `is_valid()`，到 `save()` 撞数据库 unique 约束抛 `IntegrityError` → 500。
2. **原有员工全进「未分组」**：迁移 `0005_branch_team` 给 `Branch.team` 加字段但 `null=True` 不回填，原有分公司 `team=null` → 进未分组 → 员工（`branch` 指向它们）跟着进。
3. **乱码**：500 时后端返回 HTML 错误页，前端 `handleApiError` 对字符串做 `Object.entries` 逐字符处理 → 一串零散字符 = 乱码。

## What Changes

- **修复 500**：`BranchSerializer.validate_code` 增加 unique 校验（编辑时排除自身），`code` 重复返回 400 而非 500。
- **数据回填**：新增管理命令 `assign_branch_team_from_employees`，按员工 `team` 众数回填分公司 `team`，支持 `--dry-run` 预览。
- **修复乱码**：`handleApiError` 处理非 JSON 响应（string/HTML），返回可读错误（含 HTTP 状态码）。

## Capabilities

### New Capabilities

- `frontend-error-display`: 前端对 API 错误响应（含非 JSON / HTML 服务器错误页）的可读展示。

### Modified Capabilities

- `unified-organization-page`: 新增「分公司编码唯一校验」「分公司 team 数据回填」两项要求。

## Impact

- **后端**：`organizations/serializers.py`（`validate_code` 加 unique）、新增 `organizations/management/commands/assign_branch_team_from_employees.py`、后端测试。
- **前端**：`utils/request.ts`（`handleApiError`）、前端测试。
- **数据**：无 schema 变更（回填用管理命令，不改迁移）。
- **部署**：前后端都改，`deploy.sh`（后端 rebuild + 前端 build，无新 migrate）；上线后执行一次回填命令。
