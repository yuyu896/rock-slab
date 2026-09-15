# 实例规格取出生行 — 技术设计

## Context

`item_spec = CharField(source='item.specification')`；出生行派生已有 供应商/单价/采购日期 先例（SerializerMethodField）。本批规格行级存 TransferLine.本批规格。

## Decisions

### D1：item_spec 改 SerializerMethodField

`get_item_spec = obj.birth_line.本批规格 if (obj.birth_line and obj.birth_line.本批规格) else (obj.item.specification or '')`。查询已有 select_related('birth_line__transfer','item') ✓ 零额外查询。

### D2：不回写字典

批次间规格可互异（同品目不同采购批），字典规格=品目默认；实例规格=个体实际（出生行）。两语义并存各归其位（铁律 1：各自只存一处）。

## Risks / Trade-offs

（无——显示层派生，零存储变更）

## Migration Plan

纯代码，随部署生效；存量实例立即按出生行显示。

## Open Questions

（无）
