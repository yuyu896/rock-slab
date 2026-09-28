# 提案：标签规范 V1——QR 码制 + 内部编号 + 双轨纸型

## Why

两个缺陷叠加，使标签打印无法支撑"贴在机器上"的核心场景：

1. **内容口径错**：CODE128 条码印的是品目编号，同品目所有实例标签一样，扫码只能落到品类，无法定位"这一台"。
2. **版面按 A4 思维**：双列网格 + 8mm 页边距，标签打印机（60×40 热敏卷纸）上会裁废；没有"一页一签"能力，批量打印出不了逐张可用的标签。

规范探讨已定稿：QR（V2/ECC M）编码内部编号、60×40 标准纸型、A4 双列保留、不加公司抬头、序列号上签（空则隐藏）。员工贴标动线：实例档案页补录完序列号 → 勾选 → 打印 → 撕下贴机。

## What Changes

- **打印输出隔离**（原单独合入的 label-print-isolation 已回退，并入本提案实施）：弹窗 Teleport 到 body + `@media print` 只输出标签，解除滚动裁剪，深色模式打印白底黑字
- **码制**：CODE128 → **QR**，内容 = 内部编号（实例唯一）；新增 `qrcode` 依赖（+`@types/qrcode` dev），**移除 `jsbarcode`**（全站唯一使用处即本弹窗）
- **内容三区制**：码区（QR 13×13mm）｜身份区（内部编号 3.2mm 等宽粗 + SN 2.8mm 等宽，SN 空整行隐藏）｜品目区（名称 3.0mm 粗 + 品目编号·分公司 2.4mm 灰）
- **版式双轨**：
  - **60×40 单签**（标签打印机）：`@page { size: 60mm 40mm; margin: 0 }`，每签 `break-after: page`，固定 40mm 高度盒防内容越界
  - **A4 双列**（普通打印机）：沿用现有上下结构卡片，码区换 QR
- **弹窗纸型切换**：默认 60×40，localStorage 记忆上次选择；常驻提示「打印时请选择实际大小/100%」
- `toPrintShape` 补传内部编号、序列号（弃用「资产编号」承载品目编号的旧形状）

## Capabilities

### New Capabilities

（无）

### Modified Capabilities

- `fa-layout-and-print`: 「固定资产表标签打印」需求升级为标签规范 V1——QR 编码内部编号、60×40/A4 双轨版式、序列号显隐、一页一签逐张可用

## Impact

- 前端：`frontend/src/views/FixedAssetList.vue`（toPrintShape）、`frontend/src/views/assets/AssetPrintDialog.vue`（QR 渲染/双轨版式/纸型切换）、`frontend/package.json`（+qrcode +@types/qrcode，-jsbarcode）
- 测试：`frontend/src/tests/views/AssetPrintDialog.test.ts` 重写断言
- 零后端/扫码端改动：`filter_keyword` 已含 `内部编号__icontains`，`BarcodeDetector` 已声明 `qr_code`
