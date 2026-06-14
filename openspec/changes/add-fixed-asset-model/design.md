## Context

当前 Asset 表是品目级别的库存汇总。固定资产（电脑、手机等）需要追踪到每台实物实例，记录序列号、供应商、使用人、在用/空闲状态。

两表关系：
```
Asset（品目）                    FixedAsset（实例）
资产编号: COMP-001 ←──────关联──────→ 资产编号: COMP-001
名称: ThinkPad T14                  序列号: SN-AAA
数量: 5（自动计算）                  使用人: 张三
在库: 3（自动计算）                  状态: 在用
                                    供应商: 联想
```

## Goals / Non-Goals

**Goals:**
- 新增 FixedAsset 模型，一条记录代表一台实物
- 通过 资产编号 关联 Asset（品目），支持一对多
- 实例数量自动同步到 Asset 的数量/在库字段
- 前端固定资产表展示实例列表，支持筛选和 CRUD
- 支持通过 Excel 导入实例数据

**Non-Goals:**
- 不改变流转模块（领用/调拨）现有逻辑，后续可扩展到实例级别
- 不影响非固定资产（耗材等）的管理方式
- 不做实例级别的流转审批流程（本次只做台账管理）

## Decisions

### 1. FixedAsset 模型设计

新增 `FixedAsset` 模型放在 `apps/assets/models.py` 中（与 Asset 同 app），关键字段：
- `asset`：FK → Asset（品目），关联到具体品目
- `资产编号`：CharField，冗余存储便于查询和 Excel 导入导出
- `序列号`：CharField，可为空（手机等无序列号的情况）
- `内部编号`：CharField，自动生成（如 COMP-001-1），唯一标识
- `供应商`：CharField
- `使用人`：CharField
- `所属部门`：CharField
- `当前状态`：在库/在用/空闲
- `分公司`：CharField + FK branch
- `入库日期`、`备注` 等

### 2. 数量同步机制

使用 Django post_save/post_delete 信号，当 FixedAsset 创建/更新/删除时，自动重新计算关联 Asset 的数量和在库数。使用 `transaction.atomic` 保证一致性。

### 3. 内部编号生成规则

格式：`{资产编号}-{序号}`，如 `COMP-001-1`、`COMP-001-2`。新增实例时自动递增序号。对于无序列号的设备（如手机），内部编号是唯一标识。

### 4. API 设计

- `GET /api/fixed-assets/`：实例列表，支持按分公司/状态/关键词/资产编号筛选
- `POST /api/fixed-assets/`：新增实例
- `PATCH /api/fixed-assets/{id}/`：更新实例（如修改使用人、状态）
- `DELETE /api/fixed-assets/{id}/`：删除实例
- `GET /api/fixed-assets/template/`：下载导入模板
- `POST /api/fixed-assets/import/`：批量导入

### 5. 前端固定资产表

改造现有 `FixedAssetList.vue`，调用新的 `/api/fixed-assets/` API。表格展示每台实物的详细信息（内部编号、序列号、供应商、使用人、状态），支持编辑和删除。

## Risks / Trade-offs

- **数据量增长** → 每台实物一条记录，但固定资产总量通常可控（千级别）
- **现有数据迁移** → 需要将现有 Asset 中 资产类目=固定 的记录拆分，每个数量 N 生成 N 条 FixedAsset 实例
- **双表一致性** → 通过信号自动同步，减少手动维护风险
