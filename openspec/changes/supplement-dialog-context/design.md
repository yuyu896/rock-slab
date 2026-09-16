# 补录弹窗上下文 — 技术设计

## Context

弹窗现仅 内部编号 + 序列号/备注输入。数据已在前端行对象（itemName/使用人/departmentName）。

## Decisions

### D1：三行只读展示

内部编号下加 品目名称/使用人/部门 三个 el-form-item（文本，空值 '-'）。零逻辑改动。

## Migration Plan

随前端构建生效。

## Open Questions

（无）
