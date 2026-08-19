## Why

固定资产导入缺少表头一致性校验（用户用错模板也能导入）；固定资产列表序号解耦后永远显示'-'。两处需修复。

## What Changes

1. **表头校验**：固定资产导入 SHALL 校验上传 Excel 的表头与下载模板（FA_TEMPLATE_HEADERS 18 列）一致（列名集合相同，顺序不限）；不一致 → 拒绝导入并提示缺少/多余的列。
2. **序号行号**：固定资产列表序号改为计算行号 `(page-1)*pageSize + index + 1`（与资产列表一致）。

## Capabilities

### New Capabilities
- `fa-template-check-and-seqno`: 固定资产导入表头一致性校验 + 列表序号改行号。
