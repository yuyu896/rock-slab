## Why

安全审计动态复现：`/api/transfers/instance-occupancy` 直接以请求参数 `branch`（分公司名）+ `asset_code` 查询 FixedAsset 并返回实例内部编号、在途单据号与状态——未声明操作码（仅需登录）、无数据范围校验。零授权的 leader 传任意他分公司名即得 200+数据，可枚举探测全系统各分公司的实例与在途单据。该接口服务于建单时的占用标注（InstancePicker），业务发起类能力按产品设计对全员开放，不能以操作码收紧，但**读取面必须收敛到授权范围**（与台账导入差异预览「不得向无权用户返回范围外台账现值」同口径）。

## What Changes

- `instance_occupancy` action：分公司名解析为 Branch 后走 `validate_branches_in_scope`（admin/全部数据豁免），范围外返回 400；无法解析的分公司名维持返回 `[]`（现状，不泄露存在性差异之外的信号）
- 前端零改动（点选器传的即调出分公司、建单必在范围内；且其本身吞错不阻断）

## Capabilities

### New Capabilities

（无）

### Modified Capabilities

- `write-authorization-scoping`: 新增「实例占用查询 MUST 限定授权范围内分公司」要求（读路径范围收敛，与既有敏感读条款同族）

## Impact

- `backend/apps/transfers/views.py`：`instance_occupancy` 接入分公司解析 + 范围校验
- `backend/tests/test_instance_occupancy.py`：新增越权/豁免/未知分公司用例
- API 行为变化：范围外分公司查询从 200（返回他司数据）变 400；合法建单流程不受影响
- 无迁移、无前端改动
