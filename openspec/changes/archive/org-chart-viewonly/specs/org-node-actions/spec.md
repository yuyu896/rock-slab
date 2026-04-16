## REMOVED Requirements

### Requirement: Edit and delete from org chart detail panel
**Reason**: 编辑和删除操作已在"人员管理"和"行政组"标签页中提供，组织架构标签页改为只读展示，避免冗余操作和误操作。
**Migration**: 使用"人员管理"标签页编辑/删除人员，使用"行政组"标签页编辑/删除行政组。

## MODIFIED Requirements

### Requirement: Person detail display in org chart tab
组织架构标签页的人员详情面板 SHALL 只展示信息，不提供编辑/删除按钮。状态字段 SHALL 以只读文字形式展示（"在职"或"已停用"）。

#### Scenario: View person detail
- **WHEN** 用户在组织架构标签页点击一个人员节点
- **THEN** 系统 SHALL 展示该人员的基本信息（姓名、角色、手机号、区域、分公司、组、上级、状态），不显示编辑/删除按钮

#### Scenario: View team detail
- **WHEN** 用户在组织架构标签页点击一个行政组节点
- **THEN** 系统 SHALL 展示该行政组的基本信息（组名、区域、组长、组员列表），不显示编辑/删除按钮
