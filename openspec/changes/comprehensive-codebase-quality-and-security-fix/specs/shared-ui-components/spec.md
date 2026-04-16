## ADDED Requirements

### Requirement: BasePagination 共享分页组件
系统 SHALL 提供一个可复用的 `BasePagination` 组件，封装 Element Plus 分页控件的常用配置（页码、每页条数、总数显示）。

#### Scenario: 视图使用共享分页组件
- **WHEN** 任何列表视图需要分页功能
- **THEN** 该视图 SHALL 使用 `BasePagination` 组件，通过 props 传入总数和当前页，通过 emit 通知页码变更

### Requirement: StatusBadge 共享状态徽章
系统 SHALL 提供一个可复用的 `StatusBadge` 组件，根据状态值自动映射颜色和文字标签。

#### Scenario: 状态徽章自动映射颜色
- **WHEN** 传入 `status="在库"` 的资产状态
- **THEN** 组件 SHALL 显示绿色徽章并标注"在库"

#### Scenario: 未知状态处理
- **WHEN** 传入未定义的状态值
- **THEN** 组件 SHALL 显示灰色默认徽章

### Requirement: ImportDialog 共享导入对话框
系统 SHALL 提供一个可复用的 `ImportDialog` 组件，封装 Excel 文件选择、上传进度、导入结果展示的完整流程。

#### Scenario: Excel 导入流程
- **WHEN** 用户点击导入按钮
- **THEN** 组件 SHALL 弹出对话框，支持文件选择、上传、显示导入结果（成功/失败条数）

### Requirement: FilterPanel 共享筛选面板
系统 SHALL 提供一个可复用的 `FilterPanel` 组件，支持动态配置筛选条件和搜索框。

#### Scenario: 配置筛选条件
- **WHEN** 视图传入筛选字段配置（如分公司下拉、状态选择、日期范围）
- **THEN** 组件 SHALL 渲染对应的筛选控件，并在用户变更时 emit 筛选参数

### Requirement: 巨型视图组件拆分
以下视图组件 MUST 拆分为多个子组件，每个文件不超过 500 行：
- `Organization.vue`（当前 ~2807 行）
- `MainLayout.vue`（当前 ~1325 行）
- `Inventory.vue`（当前 ~2070 行）
- `AssetList.vue`（当前 ~1990 行）
- `Category.vue`（当前 ~1620 行）
- `Purchase.vue`（当前 ~1430 行）

#### Scenario: 拆分后功能不变
- **WHEN** 完成组件拆分
- **THEN** 所有现有功能 SHALL 保持不变，无视觉或交互差异
