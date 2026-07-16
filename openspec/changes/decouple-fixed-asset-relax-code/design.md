## Context

- `Asset.资产编号` 现为 `unique=True`（全局唯一）；导入去重 `(分公司, 资产编号)`。
- `FixedAsset.asset` 为必填外键（`on_delete=CASCADE`）；导入按 资产编号 查父 Asset；`signals.py` 在 FixedAsset 增删时同步 `Asset.数量 = FixedAsset.count()`。
- 固定资产导出(19 列)从父 Asset 取 序号/资产类目/物品分类/资产名称。
- 固定资产已有自身字段：分公司/分公司编号/资产编号/资产名称/序列号/供应商/物品分类/入库日期/是否租用/数量/规格/单价/购入金额/出库日期/所属部门/使用人/当前状态/备注/内部编号。无 资产类目。

## Goals / Non-Goals

**Goals:**
- 资产编号可重复（不同所属部门/规格时）；所属部门必填；四元组表内去重。
- 固定资产与 Asset 解耦；资产编号校验存在于品目。

**Non-Goals:**
- 不改资产/固定资产的模板列（已定稿）。
- 不改固定资产 (分公司+序列号) 去重/唯一约束。
- 不做品目→固定资产的反向关联（仅校验存在）。

## Decisions

### 决策 1：资产编号去 unique + 四元组去重
- **做法**：`Asset.资产编号` 去 `unique=True`（迁移 AlterField）；导入去重 key 改为 `(分公司, 资产编号, 所属部门, 规格)`；所属部门空 → 拒。
- **理由**：业务上同编号可跨部门/规格重复。

### 决策 2：固定资产 asset 外键移除 + 资产类目字段
- **做法**：`FixedAsset.asset` 外键移除（迁移 RemoveField）；新增 `资产类目` 字段（CharField blank，导入时从品目取）。
- **理由**：解耦；资产类目供导出/展示（原来从父 Asset 取，现从品目/FixedAsset 自身取）。

### 决策 3：固定资产导入校验品目
- **做法**：导入不再 `Asset.objects.get(资产编号=…)`；改为 `Category.objects.filter(asset_code=资产编号).exists()` 校验；资产类目/物品分类/资产名称 缺省从品目取（文件值优先）。
- **理由**：固定资产挂在品目上。

### 决策 4：移除数量同步信号
- **做法**：移除 `signals.py` 的 `_sync_asset_counts` + `on_fixed_asset_save/delete` 连接。
- **理由**：解耦后 Asset.数量 不再自动等于固定资产数。
- **影响**：`Asset.数量` 改为按导入/手填值，不再随固定资产增删自动变。

### 决策 5：导出改用自身字段
- **做法**：固定资产导出 序号/资产类目/物品分类/资产名称 等从 FixedAsset 自身字段取（资产类目已有、序号可用行号或留空）。
- **理由**：不再有父 Asset 可取。

## Risks / Trade-offs

- **[Asset.数量 行为变化]** 解耦后不再自动同步 → 用户需知：资产列表数量不再等于固定资产数。**接受**（解耦诉求）。
- **[去 unique 迁移]** 去 `Asset.资产编号` unique 是不可逆的 schema 变更 → 部署前备份（deploy.sh 已含）。
- **[删外键迁移]** 移除 FixedAsset.asset 是破坏性迁移（列删除）→ FixedAsset 数据行保留，仅丢失与 Asset 的关联链接（符合解耦意图）。
- **[历史固定资产 资产类目空]** 既有记录无 资产类目 → 导出时空或按品目回填（可后续脚本）。

## Migration Plan

1. 模型：Asset 去 unique；FixedAsset 去 asset 外键 + 加 资产类目 字段。
2. 信号：移除同步。
3. 导入：资产四元组去重 + 所属部门必填；固定资产品目校验。
4. 导出/序列化器：清理 asset 引用。
5. 部署：`bash deploy.sh`（含 migrate）。

## Open Questions

1. 历史固定资产记录的 资产类目 是否需要回填？默认**不回填**（新导入的从品目取；历史留空）。
