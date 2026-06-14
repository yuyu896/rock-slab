## ADDED Requirements

### Requirement: Export button in header
固定资产表页面头部 SHALL 在批量导入按钮左侧显示"导出"按钮，仅具有资产管理权限的用户可见。

#### Scenario: Export button visible for authorized users
- **WHEN** 用户拥有资产管理权限（canManageAssets）
- **THEN** 页面头部显示"导出"按钮，位于批量导入按钮左侧

#### Scenario: Export button hidden for unauthorized users
- **WHEN** 用户无资产管理权限
- **THEN** 页面头部不显示"导出"按钮

### Requirement: Export fixed assets to Excel
用户点击导出按钮后，系统 SHALL 将当前筛选条件下的固定资产数据导出为 Excel 文件并触发浏览器下载。

#### Scenario: Export with active filters
- **WHEN** 用户设置了分公司或状态筛选条件后点击导出
- **THEN** 系统请求导出接口并传入当前筛选参数，浏览器下载包含匹配数据的 Excel 文件

#### Scenario: Export with no filters
- **WHEN** 用户未设置任何筛选条件时点击导出
- **THEN** 系统导出全部固定资产数据为 Excel 文件

#### Scenario: Export failure
- **WHEN** 导出接口返回错误
- **THEN** 页面显示错误提示消息
