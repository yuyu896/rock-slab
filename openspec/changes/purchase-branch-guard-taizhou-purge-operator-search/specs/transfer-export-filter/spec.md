# transfer-export-filter 增量

## ADDED Requirements

### Requirement: 流转关键字搜索匹配经办人

流转列表的关键字搜索（keyword）MUST 扩展匹配 `采购经办人` 与 `创建人`（icontains，与单号/品目编号/品目名称/调出分公司/调入分公司并列 OR）；导出透传同一参数口径不变。前端各流转列表搜索框提示文案 MUST 含经办人。

#### Scenario: 按经办人搜单

- **WHEN** 用户在采购列表搜索框输入经办人姓名「张三」
- **THEN** 列表返回 采购经办人 或 创建人 含「张三」的单据（与单号/品目匹配并集）
