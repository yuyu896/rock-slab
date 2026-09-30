## Context

`instance_occupancy`（backend/apps/transfers/views.py:512-528）以 `branch`（分公司名）+ `asset_code` 直查 FixedAsset，返回 `instanceId/instanceCode/docNo/docStatus`（在途单据占用标注，InstancePicker 消费）。调用方 TransferLinesEditor 传入的 branchName 与 getAssetStocks 同源——即调出/来源分公司，建单路径已强制其在授权范围内（调拨类型仅校验调出方，spec 修订 3.1）；前端对该接口吞错不阻断（「预检为权威闸门」）。`core/permissions.validate_branches_in_scope(user, *branch_values)` 现成：admin/全部数据豁免，越界抛 DRF ValidationError（400）。

## Goals / Non-Goals

**Goals:**

- 占用查询的读取面收敛到操作者授权范围：范围外分公司 400，不再返回他司实例编号/单据号
- 合法建单流程（本范围调出方）行为不变；admin/全部数据授权全量可用

**Non-Goals:**

- 不给该 action 声明操作码（业务发起辅助读，全员开放是既有产品语义）
- 不改占用映射逻辑（`_pending_occupation_map`）与响应结构
- 不处理 asset_code 维度（品目编号本身全系统唯一且字典对所有用户可读）

## Decisions

**1. 校验手段：分公司名 → Branch 实例 → `validate_branches_in_scope(user, branch.id)`。**
复用现成闸门（与写路径同一错误文案/形态），不另造判定。按名解析沿用现有入参契约（前端传名），不改为 id（避免联动前端）。

**2. 名字解析失败的语义：返回 `[]`（维持现状）。**
未知分公司名现在就是空结果；改成 400 会引入新的存在性信号差异。分公司名本身经组织树对全员可见，400（范围外）不构成额外泄露。两者并存：**能解析但范围外 → 400；不能解析 → []**。

**3. 缺参（branch 或 asset_code 为空）维持 `[]`。**
现状语义，无泄露面。

## Risks / Trade-offs

- [若未来前端把调入方分公司传给点选器（跨范围调拨场景），会得 400 且标注缺失] → 现网仅传调出方；且前端吞错不阻断，最坏是少一行占用标注（预检仍是权威闸门）
- [分公司同名（重名）时 filter(branch__name=…) 现状本就歧义] → 本变更按 `.first()` 取首个判定范围，行为不劣于现状；重名治理另案

## Migration Plan

纯代码，无迁移。部署即生效；回滚 revert。上线验证：以本分公司账号传他分公司名应 400，传本公司名应 200。
