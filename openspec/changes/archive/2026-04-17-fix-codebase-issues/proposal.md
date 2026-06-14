## Why

项目全面检查发现前端存在模板死引用、数据绑定不一致、类型定义与实际使用脱节等问题，后端存在已弃用 API 和未使用 import。这些问题会导致运行时警告、潜在的数据提交错误，且增加维护成本。应尽早修复以保持代码库健康。

## What Changes

- 修复 `MobileAssign.vue` 模板中引用已删除字段 `form.所属部门` 的 v-model 死引用，改为使用有效的表单字段
- 修复 `MobileAssign.vue` 分支选择器使用 `branch.name` 而非 `branch.id` 的不一致问题，与 `MobileTransfer.vue` 等其他视图保持一致
- 更新 `types/index.ts` 中 `Transfer` 接口，添加 `fromBranch`/`toBranch` 字段别名，消除前端代码中 `as any` 强制转型的需求
- 替换 `audit/views.py` 中已弃用的 `.extra()` 调用为 Django 推荐的 `TruncDate`
- 清理 `reports/views.py` 中未使用的 import（`ROLE_LEVELS`、`F`）
- 清理 `assets/views.py` 中未使用的 import（`IsAdmin`）

## Capabilities

### New Capabilities

_(无新能力引入)_

### Modified Capabilities

_(无现有 spec 需要变更，这些都是代码层面的修复)_

## Impact

- **前端文件**: `MobileAssign.vue`（模板 + 逻辑）、`types/index.ts`（类型定义）
- **后端文件**: `audit/views.py`、`reports/views.py`、`assets/views.py`
- **无 API 变更**: 所有修复均为内部代码质量改进，不改变外部接口行为
- **无数据库变更**: 不涉及 migration
