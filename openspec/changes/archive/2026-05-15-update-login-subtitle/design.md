## Context

登录页面 `Login.vue` 第 74 行的副标题当前为"资产管理系统"，需修改为"行政资产盘点"以匹配产品定位。

## Goals / Non-Goals

**Goals:**
- 将副标题文案更新为"行政资产盘点"

**Non-Goals:**
- 不涉及登录页面布局、样式或逻辑的任何变更

## Decisions

直接修改 `Login.vue` 模板中的硬编码文案。无需抽取为常量，因为该文案仅在登录页使用一次。

## Risks / Trade-offs

无风险。纯文案替换。
