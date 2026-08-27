## 1. 后端软预检

- [x] 1.1 `validate_line_items_instances` 增回收分支：数量管理品目按（from_branch×品目）合并计量，查 AssetStock 当前在用（行缺失视为 0），超出抛 ValidationError（业务文案含当前在用/需回收数量）
- [x] 1.2 确认三路径（创建/驳回后编辑/Excel 导入）均经该函数且报错可达前端

## 2. 测试与验证

- [x] 2.1 pytest：创建超在用 400、多行同品目合并计量 400、驳回后编辑超在用 400、在用足够正常创建、台账行缺失视为在用 0
- [x] 2.2 全量回归：pytest 通过（既有回收链路测试不受影响）

## 3. 收尾

- [x] 3.1 v2-revision-draft.md §八 第 7 案状态改 ✅（含排查结论与生产处置记录）；feat + openspec 两 commit → push → 归档
