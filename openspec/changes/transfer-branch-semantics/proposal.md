# 单据分公司语义化——收口 from/to 直摸，按业务语义建单

## Why

5 类单据共用一张 Transfer 表，分公司借调拨的「调出/调入」双向命名、按类型单边复用（采购只用调入、领用等只用调出）——字段语义与业务错位全靠人为约定，第 24 案的「采购导入分公司装反到调出方」正是缺结构约束的产物。根治：建单路径收口到语义化构造器，模型暴露类型化业务属性，架构测试禁止业务代码再直接赋值 from/to。

## What Changes

- `Transfer.build()` 语义化构造器：采购/领用/归还/回收收 `所属分公司`（采购落 to、其余落 from）、调拨收 `调出/调入`——映射唯一收口在模型内
- `Transfer.业务分公司` 属性：按类型返回货账归属方（采购→to_branch，其余→from_branch），供读取方使用
- 两处建单调用点（`_create_action` 页面创建、`import_excel` 批量导入）改走 `build`
- 架构测试执法：apps/ 业务代码禁止 `from_branch=`/`to_branch=` 赋值（白名单：models.py 自身、migrations、tests）
- 非目标：数据库列不改名（避免全链路迁移）；API 契约/序列化输出不变（前端已按业务名展示）；读取方（ledger/instances/序列化）逐步迁移不强制本次

## Capabilities

### New Capabilities

（无）

### Modified Capabilities

- `transfer-line-items`: 单据创建分公司路径收口——语义化构造器唯一入口，架构测试禁直赋

## Impact

- **后端**: `transfers/models.py`（build + 业务分公司属性）、`views.py` 两调用点、架构测试
- 前端零改动；无迁移；API 不变
