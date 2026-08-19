## Context

- 资产列表「下载模板」按钮经 `AssetImportDialog` → `generateAssetTemplate()`（`utils/importTemplate.ts`）**前端生成** xlsx，表头取自常量 `ASSET_HEADERS`（旧 23 列）。
- 后端 `/api/assets/template` 已是 15 列，但前端不调用它——用户下载的是前端这份。
- 资产导入按列名解析，模板列与导入解析解耦；改 `ASSET_HEADERS` 不影响导入。

## Goals / Non-Goals

**Goals:** 用户下载的资产模板恰为指定 15 列。
**Non-Goals:** 不改后端模板（已正确）；不把前端改为调后端（保持客户端生成，最小改动）；不动固定资产模板。

## Decisions

### 决策 1：直接更新前端 `ASSET_HEADERS`
- **做法**：`ASSET_HEADERS` 改为指定 15 列。
- **理由**：前端生成模板的表头即此常量；改它即修复用户所见。备选（前端改调后端）改动大、非本次诉求。

## Risks / Trade-offs

- **[前后端模板双源]** 后端 `/api/assets/template`（15 列）与前端 `ASSET_HEADERS`（将改 15 列）两套来源，未来可能再分叉 → **缓解**：本次对齐为同一 15 列；后续可统一为后端单一来源（非本次范围）。

## Migration Plan

前端常量改动，无 DB 迁移；前端 build 后生效。

## Open Questions

（暂无。）
