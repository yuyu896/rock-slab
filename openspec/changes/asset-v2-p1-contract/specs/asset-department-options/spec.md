## REMOVED Requirements

### Requirement: 资产明细所属部门预置选项与自定义输入
**Reason**: 资产明细表单随 Asset 冻结只读而下线，前端常量 `DEPARTMENT_PRESETS` 的硬编码方案同时废止；部门选项统一由部门字典提供（分公司维度）。
**Migration**: 所有部门输入（固定资产创建、流转单创建）接部门字典下拉，见 `department-dictionary` 能力。
