# asset-code-and-fixed-asset-decouple Specification

## Purpose
TBD - created by archiving change decouple-fixed-asset-relax-code. Update Purpose after archive.
## Requirements
### Requirement: 资产编号可重复（四元组去重）
资产导入 SHALL 允许资产编号重复——当所属部门或规格不同时不算重复；仅「同分公司 + 同资产编号 + 同所属部门 + 同规格」全同时才判定为重复。

#### Scenario: 不同所属部门允许同编号
- **WHEN** 同一导入文件含两行：同分公司、同资产编号、**不同所属部门**
- **THEN** 两行都导入成功

#### Scenario: 四元组全同被判重复
- **WHEN** 两行分公司/资产编号/所属部门/规格全同
- **THEN** 第二行被判重复、跳过并提醒

### Requirement: 资产导入所属部门必填
资产导入 SHALL 要求「所属部门」非空；空 → 拒行并提醒。

#### Scenario: 所属部门为空被拒
- **WHEN** 某行所属部门为空
- **THEN** 该行被拒、提醒所属部门为空

### Requirement: 固定资产不再关联资产库存
FixedAsset SHALL 不再通过外键关联 Asset；固定资产导入 SHALL 不查父资产。

#### Scenario: 导入不查父资产
- **WHEN** 通过固定资产模板导入一行
- **THEN** 不执行 Asset 查找（即使资产编号在资产列表中不存在也不报错，只要在品目中存在即可）

### Requirement: 固定资产资产编号须存在于品目
固定资产导入 SHALL 校验「资产编号」存在于品目（Category.asset_code）；不存在 → 拒行并提醒。

#### Scenario: 资产编号不在品目被拒
- **WHEN** 固定资产导入某行资产编号不在品目中
- **THEN** 该行被拒、提醒资产编号未在品目登记

#### Scenario: 资产编号在品目可导入
- **WHEN** 资产编号存在于品目
- **THEN** 该行正常导入（资产类目等从品目取缺省值）

### Requirement: 移除固定资产对资产数量的同步
系统 SHALL 不再在固定资产增删时自动更新 Asset.数量。

#### Scenario: 新增固定资产不影响资产数量
- **WHEN** 创建/删除一条固定资产
- **THEN** Asset.数量 不因此变化

