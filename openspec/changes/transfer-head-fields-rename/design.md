## Context

Transfer 单头两处化石命名：`调拨日期 = DateField(verbose_name='调拨日期')`（0001 出生，五类共用业务日期，API key 与列标签混用至今）、`调拨原因 = TextField`（通用事由）。后端 58 处、前端 46 处（另移动端 4 页）引用。标签层已场景化：导入模板列 采购日期/日期/调拨日期/回收日期、界面标签（回收场景=回收日期）、导出列名——这些**用户可见字符串**与**库字段名**在代码里同名混居，是本次实施的最大风险点（改错一类即断）。

## Goals / Non-Goals

**Goals:**

- 库字段名/API key/代码引用统一为 `单据日期`、`事由`；verbose_name「流转单记录」
- 用户可见的列标签、模板表头、界面文案、Excel 兼容性零变化
- 存量数据无损（RenameField）

**Non-Goals:**

- 列标签/表头/文案（已场景化）
- `调出/调入分公司`、`调拨数量` 等调拨专属或行列名
- 编号生成、台账、审批等任何行为变化

## Decisions

### D1：手写 RenameField 迁移，禁止 makemigrations 自动生成

0021 教训：非交互模式对改名退化为 RemoveField+AddField 会清空列数据。手写 0028（`调拨日期→单据日期` + `调拨原因→事由` 两条 RenameField + verbose_name 随模型自动带入）——RenameField 元数据级，SQLite/PG 均安全；本地 migrate 后用行数与非空计数验证无损。

### D2：引用替换按「语境三分法」收口，禁止盲目全局替换

`调拨日期` 在代码中有三种身份，逐处判定：
1. **字段引用**（模型属性/序列化 key/ORM 查询/排序/筛选/header dict 键）→ 改 `单据日期`
2. **用户可见列标签**（TYPE_TEMPLATES 表头、导出 headers 列表、模板样例列名、`_num(row,'采购日期')` 等按列名读取）→ **不动**
3. **注释/文档字符串** → 跟随改（可读性）

`调拨原因` 同理（transfer 模板列「调拨原因」是标签，保留；字段引用改「事由」）。收口判据：`grep -rn "调拨日期" backend/apps frontend/src`（排除 migrations/标签白名单清单）为零，白名单清单在 tasks 记录。

### D3：前端 key 全链路同步

五类创建页 `form.调拨日期→form.单据日期`（标签 input 的 v-model 与模板标签各自独立——标签文案不动）、payload key、列表 `item.调拨日期`、详情 `doc.调拨日期`、types `调拨日期?: string`、移动端 4 页同构。API key 变化由前后端同一次部署吸收（同仓原子，无版本偏斜客户端）。

## Risks / Trade-offs

- [标签与字段同名语境误改（最大风险）] → D2 三分法逐处判定 + 收口 grep 白名单；门禁全量测试兜底（夹具里两类引用都有，改错即红）
- [RenameField 在 PG 的锁行为] → 单列元数据级毫秒完成，无 DML 混排
- [遗漏引用导致运行时 500] → 后端 58+前端 46 处清单化逐一处理；`python manage.py check` + 全量 pytest + build 三道门禁

## Migration Plan

单迁移 0028（两条 RenameField，纯 DDL）。部署常规 deploy.sh；上线后抽查任一单据详情日期正常、导入导出列名不变。回滚：迁移可逆（RenameField 对称），代码回退即可。

## Open Questions

（无——范围经探讨拍板：两字段一 verbose_name，标签零变化。）
