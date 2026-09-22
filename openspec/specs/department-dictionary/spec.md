# department-dictionary Specification

## Purpose
TBD - created by archiving change asset-v2-p1-contract. Update Purpose after archive.
## Requirements
### Requirement: 部门字典模型

系统 SHALL 提供部门字典 `Department`：字段为部门名称（全集团扁平，无分公司维度），`部门名称` MUST 全局唯一。部门是归属标签而非组织树节点，MUST NOT 参与组织树层级与数据范围推导。

#### Scenario: 重复部门名被拒

- **WHEN** 字典已有「行政部」，再创建「行政部」
- **THEN** 创建被拒绝并提示已存在

#### Scenario: 存量分公司维度合并

- **WHEN** 迁移执行时存在 68 条同名「行政部」（分属不同分公司）
- **THEN** 合并保留一条「行政部」，引用其的领用行/盘点任务/实例档案 FK 全部重指向该行，历史展示的部门名称不变

### Requirement: 部门字典管理与选项接口

系统 SHALL 提供部门字典的新增、编辑、删除、列表接口（写操作要求相应管理权限），并 SHALL 提供部门选项下拉端点返回全集团部门全集（不按分公司过滤）。

#### Scenario: 选项端点返回全集

- **WHEN** 用户在任何表单中请求部门选项
- **THEN** 返回全集团扁平部门列表（~8 条），与所选分公司无关

### Requirement: 存量部门文本归一迁移
系统 SHALL 提供存量归一迁移：扫描 Asset.所属部门、FixedAsset.所属部门、Transfer 的调出/调入/需求部门五处文本，按分公司分组去重生成归一预览清单（含分公司缺失、空白部门的异常行），人工确认后生成字典行。既有业务字段的文本值 P1 保持不变（FK 化在 P2 随领用单绑部门进行）。

#### Scenario: 预览清单暴露异常行
- **WHEN** 存量数据中某 Asset 部门为「市场部」但 branch 为空
- **THEN** 预览清单将该行列入异常区，提示人工判定分公司归属

#### Scenario: 确认后生成字典行
- **WHEN** 管理员确认预览清单，执行归一
- **THEN** 各分公司生成对应部门字典行，去重后的清单计数与生成数一致

### Requirement: 表单部门输入接字典

固定资产创建页与流转单创建页（调出部门、调入部门、需求部门）的部门输入 SHALL 以下拉呈现，选项来自部门字典全集（不再按分公司过滤）。

#### Scenario: 下拉展示字典全集

- **WHEN** 用户在采购单创建页聚焦「需求部门」下拉
- **THEN** 列出全集团部门字典项，与所选入库分公司无关

