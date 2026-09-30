## 1. 实现

- [x] 1.1 `backend/apps/assets/views.py` supplement：部分更新语义；非空序列号全局查重（exclude 自身），重复 400 挂 `序列号` 字段。**配套**：`FixedAssetSupplementSerializer` 两字段去掉 `default=''`（DRF 默认值会进 validated_data，破坏部分更新判定）
- [x] 1.2 新增 `backend/core/management/commands/report_serial_duplicates.py`：分组输出重复明细，有重复非零退出

## 2. 测试

- [x] 2.1 新增 `tests/test_serial_uniqueness.py` 7 例：重复 400 且首台不变、唯一通过、只补备注保序列号、显式空串退回待补录、重提交自身序列号不误判、命令非零/零退出
- [x] 2.2 全量 `pytest` 通过（902 passed / 5 skipped / 6 xfailed）

## 3. 收尾

- [ ] 3.1 手验要点记录（补录页试录重复序列号应得明确 400 提示）

> 手验要点：实例列表对某台补录一个已存在的序列号应得「已被其他实例使用」400；只改备注时序列号不丢；生产处置后跑 `python manage.py report_serial_duplicates` 应零退出。

## 4. 口径修订（2026-09-30 探讨定案，已实施）

- [x] 4.0 查重口径全局→同分公司（supplement/batch_update/report_serial_duplicates 三处），跨分公司同号放行；定案依据：序列号列=电脑厂商 SN+手机行政自编编号，自编编号跨分公司撞号合法、空序列号合法终态（不设确认缺失流程）

## 5. 阶段二（另行变更，存量清理完成后）

- [ ] 5.1 用户按 docs/序列号重复清单_20260930.csv 人工处置 47 台（真没号的清空即合法终态）→ `report_serial_duplicates` exit 0 → 新迁移加 `UniqueConstraint(branch, 序列号, condition=非空)` + 「待补录」规范措辞调为工作清单口吻
