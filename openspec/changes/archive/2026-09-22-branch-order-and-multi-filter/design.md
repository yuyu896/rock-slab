## Context

调查结论见 proposal（编码失控/单选组件九页共用/两层排序叠加）。用户四项拍板（2026-09-22）：排序按**名称拼音**；测试公司不处理；多选无特殊要求；采购排序采推荐方案且**五种单据统一**生效。

## Goals / Non-Goals

**Goals:**
- 分公司选项全站按名称拼音呈现（下拉/树/选择器）
- 分公司筛选支持多选（九个消费页全部）
- 流转列表统一"待审批→草稿→其余+日期倒序"跨页一致

**Non-Goals:**
- 不治理分公司编码（测试公司 CS002/CS003 保留、前缀/位数规范不做）
- 不改后端 Branch.Meta.ordering（code 序保留为接口默认，展示序由前端收口）
- 不做大区/行政组层级排序（B 案否决）

## Decisions

| 决定 | 理由 |
|------|------|
| 分公司排序在**前端**做：共享工具 `sortBranchesByName`（`localeCompare(_, 'zh')`）收口，应用点=BranchFilterSelect 内部、创建页分公司下拉（采购/领用/调拨/回收）、组织架构树分公司节点 | 中文拼音序后端不可靠（PG collation 大概率按码点）；前端 localeCompare 稳；零迁移零数据变更 |
| 多选值语义**沿各页现状口径**（流转=分公司名、资产=分公司编号、盘点=branch id），仅从单值变多值 | baseline 明示三种口径并存（branch-filter 规格），统一口径是另一个大手术且无收益 |
| 多选参数形态：组件回传 `string[]`（`[]`=全部），请求层 `join(',')` 单参数传输，后端各过滤器按逗号切分→`__in` | 单参数最简、日志可读、django-filter 无需 getlist |
| BranchFilterSelect 改 `ElSelect multiple + collapse-tags`，去掉「全部分司」单项（清空=全部） | 多选模式下空数组即全部，'' 哨兵项无意义且会混入选中集 |
| 五单据排序统一在**后端列表端点**：`Case(待审批→0, 草稿→1, 其余→2)` 注记 → `-调拨日期` → `-created_at`；前端删 PurchaseList 页内 `sortedTransfers` | 翻页一致根治；无中文排序依赖（状态是等值比较）；五种单据一致口径（用户选 a） |
| 分公司名次序从排序键中**移除** | 经办人单公司视角空转；admin 分组浏览诉求由多选筛选承担；回避后端拼音序坑 |

## Risks / Trade-offs

- [九页多值化改造漏改] → grep `BranchFilterSelect` 全量清点（9 页）逐页核字段口径；vitest+build 兜底
- [useTransferList 共享 filters 的列表与独立筛选页行为不一致] → 流转四页在 composable 一处改；资产/盘点/调整记录页单独核
- [多选全选大结果集慢] → 现单选"全部"同样全量，无回归；分页上限既有
- [前端删页内排序后草稿不再置顶第二？] → 后端 rank 已含草稿第二，行为保持
- 回归面：branch-filter 既有规格的四条 Requirement 全部保持（命中语义不变，仅单值→多值）
