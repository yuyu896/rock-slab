## 1. 移动员工支持分公司置空

- [x] 1.1 在 `frontend/src/views/Organization.vue` 的 `confirmMove()` 中移除 `!s?.branch` 守卫（去掉第 174 行的 warn 返回），改为允许空 branch 提交（发送 `{ branch: s.branch || null }`）
- [x] 1.2 在移动弹窗的分公司选择器上添加 `clearable` 属性，使用户可以手动清空选择
- [x] 1.3 验证：选中员工 → 移动 → 清空分公司 → 确认，员工 branch 变为 null，在集团根节点员工列表中可见

## 2. 实例档案导出补字段

- [x] 2.1 在 `backend/apps/assets/views.py` 的 `FA_EXPORT_HEADERS` 列表（约第 608 行）末尾追加 `'备注'` 和 `'管理方式'` 两项，共 15 列
- [x] 2.2 在 `export_excel` action 的行数据组装处（约第 628-642 行），追加两个字段：`data.get('备注', '')` 和 `Category.MANAGEMENT_LABELS.get(data.get('managementType', ''), data.get('managementType', ''))`（需 import Category 或直接用字典映射）
- [x] 2.3 验证：在实例档案页点击导出，打开下载的 xlsx 文件，确认第 14 列为备注内容、第 15 列为中文管理方式标签

## 3. ItemPicker 管理方式筛选 + placeholder 提示

- [x] 3.1 在 `frontend/src/components/ItemPicker.vue` 的 `defineProps` 中新增可选 prop `managementType?: string`
- [x] 3.2 全量字典模式的 `getCategories` 调用处，添加 `管理方式: props.managementType || undefined`
- [x] 3.3 台账模式结果的 `.filter()` 链，在现有 `excludeConsumable` / `excludeInstance` 之后追加 `!(props.managementType && c.管理方式 !== props.managementType)` 过滤
- [x] 3.4 将 `placeholder` computed 中的缺省文字从 `'输入编号或名称检索品目'` 改为 `'支持按编号或名称搜索'`
- [x] 3.5 验证：在新增领用单页面，ItemPicker 能按管理方式筛选品目，且搜索框默认 placeholder 文字已更新

## 4. 类型检查与构建

- [x] 4.1 在前端根目录运行 `npm run build`，确认 TypeScript 类型检查零错误、构建成功
