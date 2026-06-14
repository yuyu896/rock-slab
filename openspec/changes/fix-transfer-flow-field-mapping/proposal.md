# 修复领用出库和调拨流转的字段映射问题

## 问题

领用出库（AssignList.vue）和调拨（TransferList.vue）的提交表单存在与采购入库相同的字段映射问题：

### 1. 领用出库（AssignList.vue）
- 表单字段 `数量`、`使用人`、`所属部门` 不匹配后端 `TransferActionSerializer` 期望的 `调拨数量`、`调拨原因`、`调出部门`
- 缺少 `调拨日期` 必填字段
- 未传递 `to_branch`/`from_branch` FK 字段（`toBranch`/`fromBranch`）

### 2. 调拨（TransferList.vue）
- 表单字段 `数量` 不匹配 `调拨数量`
- 缺少 `调拨日期` 必填字段
- `调出分公司`/`调入分公司` 用的是字符串而非 `fromBranch`/`toBranch` FK
- 后端 `CamelCaseJSONParser` 会把 camelCase 转 snake_case，需用 camelCase 传 FK 字段

### 3. 后端 TransferActionSerializer
- CharField 缺少 `allow_blank=True`（已在采购入库修复中处理）

## 影响范围

- `frontend/src/views/transfers/AssignList.vue` — 领用表单字段映射
- `frontend/src/views/transfers/TransferList.vue` — 调拨表单字段映射
- `frontend/src/views/mobile/MobileAssign.vue` — 移动端领用（如有同样问题）
- `frontend/src/views/mobile/MobileTransfer.vue` — 移动端调拨（如有同样问题）
