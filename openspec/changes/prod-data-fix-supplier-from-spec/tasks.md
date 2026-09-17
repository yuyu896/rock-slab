# 任务：规格错填供应商数据纠错

## 1. 命令实现

- [ ] 1.1 `backend/apps/transfers/management/commands/prod_data_fix_supplier_from_spec.py`：圈定规则（电脑精确四值/手机包含三关键词）、供应商保护跳过、dry-run 默认 + `--apply`、明细输出（单据编号/品目/行号/规格原值/分类统计）
- [ ] 1.2 单元测试：电脑精确命中、手机包含命中、跨类不命中、供应商已有值跳过、dry-run 不落库、幂等（apply 后再跑 0 命中）

## 2. 验证与执行

- [ ] 2.1 `pytest` 全量通过
- [ ] 2.2 本地造数 dry-run/apply 演练，核对实例档案规格列清空、供应商列归位
- [ ] 2.3 生产执行：pg 备份 → dry-run 明细发用户确认口径 → --apply → 复跑 dry-run 零命中 → 实例档案抽查
