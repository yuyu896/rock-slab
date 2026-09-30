## Context

supplement（assets/views.py 补录 action）：`instance.序列号 = serializer.validated_data.get('序列号','')` 直接兜底覆盖——未提交即清空，且无查重。batch_update 已有全局查重（`filter(序列号=sn).exclude(pk=…)` → 行级 error）。0008 删除 (分公司+序列号) 唯一约束的原因（老导入五元组去重）已随该导入下线消失。生产存量 12 组重复待人工清理——DB 约束必须等清理后引入，否则迁移失败卡部署。

## Goals / Non-Goals

**Goals:**

- 应用层全量收口：所有能写 序列号 的路径（supplement/batch_update）都拒绝全局重复
- 补录部分更新语义：未提交字段不误清
- 提供可重复执行的重复报告命令（清理验收 + 巡检）
- 为阶段二的 DB 约束铺路（数据清洁后一键可加）

**Non-Goals:**

- 本期不加数据库约束、不做数据清洗（用户人工处置，完成后另提变更引入条件唯一约束）
- 不改 batch_update 的批量错误收集形态（行级 errors 语义保留）
- 不做序列号格式校验（长度/字符集规则未定，另案）

## Decisions

**1. 查重在 supplement 内联（raise 语义），不复用 batch_update 的行级收集。**
两路径错误形态不同（单对象 400 vs 批量 errors 列表），共享同一判定表达式（`filter(序列号=).exclude(pk=).exists()`）即可，不为三行逻辑造抽象。

**2. 部分更新以 `in validated_data` 判定提交与否。**
FixedAssetSupplementSerializer 本就只透传提交字段；`'序列号' in validated_data` 是「用户显式提交」的精确信号（显式提交空串=有意清空回待补录，仍属合法操作——待补录是系统原生状态）。查重只对非空值做。

**3. 报告命令非零退出但不进部署门禁。**
非零退出码便于脚本化验收（清理后跑一次应 exit 0）；不进 deploy.sh/pytest 门禁——清理前的每次部署不该被它卡住。阶段二引入约束时，约束本身就是最终门禁。

**4. 阶段二的约束形态（本设计仅记录）：** `UniqueConstraint(fields=['序列号'], condition=~Q(序列号=''), name='unique_serial_global')`——非空全局唯一。引入前跑一次报告命令确认 exit 0。

## Risks / Trade-offs

- [应用层查重在并发下可穿透（两请求同时过 exists 检查）] → 阶段二 DB 约束兜底前的窗口期风险，接受（写入路径低频、管理员操作）
- [补录显式提交空串=清空序列号] → 语义上这是合法的「退回待补录」，与误清（未提交被兜底清空）有本质区别，行为更正而非收窄

## Migration Plan

纯代码+新命令，无迁移。部署即生效。阶段二（另提变更）：用户按 docs/序列号重复清单_20260930.csv 人工处置 47 台 → `report_serial_duplicates` 确认无重复 → 新迁移加条件唯一约束。
