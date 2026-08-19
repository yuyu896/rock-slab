## Why

分公司编号（`Branch.code`）是 Branch 模型与 `Asset.分公司编号` 之间的关联键，用于盘点筛选、报表数据隔离、采购入库等核心业务。但系统仅依赖数据库 `unique` 约束，没有任何格式校验——用户可以输入任意字符串（含空格、特殊字符、不一致大小写），容易导致数据不一致和关联失败。

## What Changes

- 为 `Branch.code` 字段添加正则格式校验，要求 `^[A-Z]{2,4}[0-9]{3}$`（2-4位大写字母城市缩写 + 3位数字序号）
- 在序列化器层自动将输入转为大写并去除首尾空格
- 前端分公司创建/编辑表单添加实时格式校验和自动大写转换
- 定义前端常量，统一管理编号格式规则

## Capabilities

### New Capabilities
- `branch-code-validation`: 分公司编号的格式规则定义、后端校验（模型+序列化器）、前端表单校验与自动格式化

### Modified Capabilities

## Impact

- **后端模型**: `backend/apps/organizations/models.py` — Branch.code 添加 validator
- **后端序列化器**: `backend/apps/organizations/serializers.py` — BranchSerializer 添加 validate_code
- **前端表单**: `frontend/src/views/Organization.vue` — 分公司编辑弹窗的 code 输入框
- **前端常量**: `frontend/src/constants/index.ts` — 新增编号格式常量
- **现有数据**: seed_data.py 中的 SH001/HZ001/GZ001 已符合新规则，无需迁移
- **API**: 无破坏性变更，仅新增校验逻辑
