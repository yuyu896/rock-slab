## 1. 前端常量定义

- [x] 1.1 在 `frontend/src/constants/index.ts` 中添加 `BRANCH_CODE_PATTERN`（正则字符串）和 `BRANCH_CODE_HINT`（格式提示文案）

## 2. 后端模型校验

- [x] 2.1 在 `backend/apps/organizations/models.py` 的 Branch.code 字段添加 `RegexValidator` 校验器
- [x] 2.2 验证 seed_data.py 中的现有编号（SH001/HZ001/GZ001）符合新规则

## 3. 后端序列化器校验

- [x] 3.1 在 `backend/apps/organizations/serializers.py` 的 BranchSerializer 中添加 `validate_code` 方法：trim 首尾空格 + 转大写 + 正则校验

## 4. 前端表单校验

- [x] 4.1 在 `frontend/src/views/Organization.vue` 分公司编辑弹窗的 code 输入框添加 `@input` 事件自动转大写
- [x] 4.2 添加 `pattern` 属性和 `placeholder` 格式提示
- [x] 4.3 添加提交前格式校验，不合规时阻止提交并提示用户

## 5. 验证

- [x] 5.1 后端测试：创建/更新分公司时校验编号格式
- [x] 5.2 前端测试：输入框自动大写和格式提示正常工作（前端无现有测试基础设施，已通过手动验证）
