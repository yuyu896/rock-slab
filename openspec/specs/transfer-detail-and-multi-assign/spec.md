# transfer-detail-and-multi-assign Specification

## Purpose
TBD - created by archiving change transfer-detail-and-multi-assign. Update Purpose after archive.
## Requirements
### Requirement: 采购入库详情为独立页面
采购入库列表的「详情」SHALL 打开独立详情页（非弹窗），展示该入库单的完整内容。

#### Scenario: 点详情跳转独立页
- **WHEN** 用户在采购入库列表点某条记录的「详情」
- **THEN** 跳转到该记录的独立详情页，展示完整字段（资产、数量、供应商、审批状态等）

### Requirement: 驳回的采购入库可修改并重新提交
已驳回的采购入库 SHALL 支持编辑字段并重新提交（审批状态由「已驳回」转为「待审批」）；非已驳回状态 SHALL 不可编辑/重提。

#### Scenario: 编辑已驳回并重新提交
- **WHEN** 用户在详情页对一条「已驳回」记录修改字段并点「重新提交」
- **THEN** 字段更新且审批状态变为「待审批」，进入审批流

#### Scenario: 非已驳回不可编辑
- **WHEN** 试图编辑或重新提交一条非「已驳回」（如待审批/已通过/已入库）的记录
- **THEN** 被拒绝（不可改、不可重提）

### Requirement: 领用出库支持多物品
新增领用出库 SHALL 支持一次添加多个物品（多行），提交时逐行创建领用流转记录。

#### Scenario: 多行提交创建多条领用
- **WHEN** 用户在新建领用出库填入多行物品并提交
- **THEN** 每行各创建一条领用流转记录（含各自的资产编号/数量/使用人）

