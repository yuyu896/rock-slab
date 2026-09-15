# fixed-asset-instance 增量

## ADDED Requirements

### Requirement: 实例规格取出生行本批规格

实例档案/生平的规格输出 MUST 取 **出生采购行的本批规格**（`birth_line.本批规格`），为空时回退品目字典规格（`item.specification`）——与 供应商/单价/采购日期 同批出生行派生口径。台账（品目级）规格 SHALL 维持取品目字典不变；MUST NOT 将本批规格回写品目字典（跨批次规格互异，回填即污染）。

#### Scenario: 本批规格优先显示

- **WHEN** 实例出生行本批规格='OPPO'、品目字典规格为空
- **THEN** 实例档案/生平规格列显示 'OPPO'

#### Scenario: 无出生行回退字典

- **WHEN** 存量迁移实例（无出生行）且品目字典规格='标准'
- **THEN** 规格显示 '标准'
