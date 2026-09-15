# 实例编号自然排序 — 技术设计

## Context

`FixedAsset.Meta.ordering = ['内部编号']`（字符串序）；编号尾段无补零 → `-10` < `-2`（字典序）→ 跨位数乱序。SQL 正则/RIGHT 提取尾段跨库困难。

## Decisions

### D1：(Length, 编号) 复合排序键

`get_queryset().order_by(Length('内部编号').asc(), '内部编号')`——Django `Length` 函数 PG/SQLite 均原生。数学：同前缀 `{P}-{seq}` 中 seq 数字越大字符串越长（无前导零）→ 长度升序=数字升序的必要条件；同长时字典序=数字序。不同品目/分公司前缀混排时先按长度后按字典，整体稳定且符合直觉（品目-分公司聚簇略受长度影响——可加前置键 `item__asset_code`？列表本就按筛选+序号场景，长度键在前会让跨品目混排轻微交错。**取舍**：键改为 `item__asset_code, branch 名?, Length, 编号`？——导出列序按分公司+品目+序号更自然。取 `Length, 内部编号` 最简且单分公司/单品目（主流场景）完全正确；跨品目混排时长短交错但同品目仍连续正确序（长度差仅当 seq 位数不同，同品目内正确）。**采用 `Length, 内部编号`**（简单正确覆盖主流）。

### D2: 仅 ViewSet 收口

Meta.ordering 不动（避免影响既有依赖默认序的路径）；`FixedAssetViewSet.get_queryset` 加排序；导出 action 走 `filter_queryset(self.get_queryset())` 自动同序。

## Risks / Trade-offs

- [跨品目混排轻微交错] — 主流场景（筛选分公司/品目后查看）完全正确；接受
- [性能] — Length 排序无索引，2 千行级全排序毫秒级；未来十万级再评估（可加函数索引）

## Migration Plan

纯代码，随部署生效。

## Open Questions

（无）
