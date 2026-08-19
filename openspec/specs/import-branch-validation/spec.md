# import-branch-validation Specification

## Purpose
TBD - created by archiving change validate-branch-on-import. Update Purpose after archive.
## Requirements
### Requirement: 资产导入校验分公司存在性
资产批量导入时，每行非空的「分公司」字段 SHALL 在组织架构 `Branch` 中存在；不存在则该行 SHALL 不被导入，并在结果 `errors` 中报错。

#### Scenario: 不存在的分公司被拒
- **WHEN** 资产导入某行的「分公司」填写了一个组织架构中不存在的名称
- **THEN** 该行不被导入（`imported` 不计该行），且 `errors` 包含提示该分公司不存在的条目

#### Scenario: 存在的分公司正常导入
- **WHEN** 某行的「分公司」是组织架构中已存在的分公司名称
- **THEN** 该行正常参与导入，不产生分公司相关报错

#### Scenario: 报错含行号与分公司名
- **WHEN** 因分公司不存在而拒绝某行
- **THEN** 报错信息包含该行行号与具体的分公司名称

#### Scenario: 空分公司被拒
- **WHEN** 资产导入某行的「分公司」为空
- **THEN** 该行不被导入并在 `errors` 提示分公司为空

### Requirement: 流转导入校验分公司存在性
流转批量导入（purchase / assign / recovery / transfer 四种类型）时，「调出分公司」以及 transfer 类型的「调入分公司」(非空) SHALL 在 `Branch` 中存在；不存在则该行 SHALL 不被导入并报错。

#### Scenario: 调出分公司不存在被拒
- **WHEN** 任一类型流转导入某行的「调出分公司」不存在于组织架构
- **THEN** 该行不被导入并在 `errors` 报错

#### Scenario: transfer 调入分公司不存在被拒
- **WHEN** transfer 类型导入某行的「调入分公司」不存在于组织架构
- **THEN** 该行不被导入并在 `errors` 报错

#### Scenario: 存在则正常导入
- **WHEN** 流转导入某行的各分公司字段均存在于组织架构
- **THEN** 该行正常参与导入

#### Scenario: 空分公司被拒
- **WHEN** 流转导入某行的「调出分公司」（或 transfer 类型的「调入分公司」）为空
- **THEN** 该行不被导入并在 `errors` 提示对应分公司为空

### Requirement: 报错与现有行级报错一致
分公司不存在的报错 SHALL 沿用各导入既有 `errors` 格式（含行号 + 中文提示），与「资产编号已存在」等既有行级报错风格一致，前端无需为此改动展示。

#### Scenario: 报错出现在 errors
- **WHEN** 导入产生分公司不存在错误
- **THEN** 该错误以与既有行级报错相同的格式出现在返回的 `errors` 中

### Requirement: 复用分公司名称查询逻辑
存在性校验 SHALL 通过统一的分公司名称查询逻辑实现（如预加载 `Branch` 名称集合的助手），资产与流转导入复用同一逻辑，避免重复实现。

#### Scenario: 两个导入使用同一查询逻辑
- **WHEN** 资产导入与流转导入分别执行分公司校验
- **THEN** 两者均由同一分公司名称查询助手驱动，行为一致

