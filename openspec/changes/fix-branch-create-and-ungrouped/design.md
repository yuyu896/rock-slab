## Context

unified-organization-page 上线后暴露三个问题（见 proposal），代码现状：

- `BranchSerializer`（`serializers.py:25-27`）：`extra_kwargs={'code':{'validators':[]}}` 清空了所有校验器（含 UniqueValidator）；`validate_code`（29-36）只做 strip/upper + regex，无 unique。
- 迁移 `0005_branch_team`：`Branch.team` `null=True` 不回填，原有分公司 `team=null`。
- `handleApiError`（`request.ts:49-60`）：`Object.entries(data)` 对 string 响应逐字符拆解 → 乱码。
- 原有数据：员工有 `team`（User.team 旧字段保留）和 `branch`；分公司 `team=null`。

## Goals / Non-Goals

**Goals:**
- 创建分公司 `code` 重复返回 400（可读），不再 500。
- 提供命令按员工 `team` 回填分公司 `team`，让原有分公司脱离未分组。
- 错误响应（含非 JSON）对用户可读。

**Non-Goals:**
- 不改 `Branch.code` 的 unique 约束本身（保留）。
- 不在前端做 unique 预检（依赖后端 400）。
- 不在迁移里自动回填（用管理命令，可审核、可预览）。

## Decisions

### D1. validate_code 手动补 unique 校验
**选择**：保留 `extra_kwargs={'code':{'validators':[]}}`（禁用 model validators），在 `validate_code` 内 regex 之后手动加 unique 检查，编辑时 `exclude(pk=self.instance.pk)`。
**理由**：`validate_code` 已做 `strip().upper()` 规范化输入和 regex，再补 unique 最直接；自定义中文错误消息。备选「去掉 extra_kwargs 让 DRF 自动恢复 model 的 regex+unique」会重新引入 model regex validator（与 validate_code 重复且不做输入规范化），故不取。

### D2. 管理命令按员工 team 众数回填
**选择**：`assign_branch_team_from_employees`。对每个分公司，统计其员工 `team`（排除 null）的出现次数，取众数赋值；无员工或员工均无 team 的分公司保持 `null`。`--dry-run` 仅打印不写库。
**理由**：用既有员工 team 数据推断分公司归属；众数容忍个别不一致员工；跳过无法推断的分公司，留给管理员手动。`--dry-run` 让管理员审核后再执行。

### D3. handleApiError 处理非 JSON 响应
**选择**：`handleApiError` 开头判断 `data` 为 string（或非对象）时，返回 `服务器错误（HTTP ${status}），请稍后重试或联系管理员`。
**理由**：`Object.entries(string)` 逐字符是乱码根因；非 JSON 响应（5xx HTML）应给通用提示 + 状态码，不暴露 HTML 内部内容。

## Risks / Trade-offs

- **[D2 回填误判]** 员工 team 与分公司实际归属不符可能误判 → Mitigation：`--dry-run` 预览 + 众数 + 管理员审核；回填后仍可在 UI 逐个调整（编辑分公司改 team）。
- **[D1 手动 unique 与 DB 约束重复]** 无害，双重保险，serializer 先拦 400。

## Migration Plan

前后端 `deploy.sh`。上线后执行：
1. `python manage.py assign_branch_team_from_employees --dry-run`（预览）
2. 确认输出合理后 `python manage.py assign_branch_team_from_employees`（执行回填）

无 schema migrate。

## Open Questions

（无。三个根因均由日志/代码确认。）
