# 实例编号自然排序 — 实施任务

- [x] 1.1 `FixedAssetViewSet.get_queryset` 加 `order_by(Length('内部编号'), '内部编号')`；测试：跨位数（-1..-12）列表顺序=数字序、导出同序
- [x] 1.2 全量 pytest；生产部署 + 线上抽查金华顺序
