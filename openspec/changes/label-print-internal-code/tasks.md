# 任务：标签规范 V1（QR + 内部编号 + 双轨纸型）

## 1. 依赖与数据形状

- [x] 1.1 `package.json`：+`qrcode`、+`@types/qrcode`（dev）、-`jsbarcode`，`npm install` 验证 lockfile
- [x] 1.2 `FixedAssetList.toPrintShape` 补传 `内部编号: item.内部编号`、`序列号: item.序列号`（弃用「资产编号」承载品目编号的旧形状）

## 2. 弹窗改造（AssetPrintDialog.vue）

- [x] 2.0 打印输出隔离（原 label-print-isolation 并入）：弹窗 `Teleport to="body"`；scoped `@media print` 去遮罩/去 `max-height` 裁剪/隐藏头脚/白底黑字固定值；非 scoped 块 `@media print` 隐藏 `#app`、body 白底
- [x] 2.1 QR 渲染替换 CODE128：`qrcode` `toString` SVG、ECC M、`margin: 0`；容器 CSS 定死 13×13mm + 2mm 静区；渲染时机沿用 `watch(visible) + nextTick`
- [x] 2.2 60×40 单签版式：左 QR 右文字横排、mm 字号（3.2/2.8/3.0/2.4）、外盒 padding 1.5mm、固定 40mm 高度盒 + `overflow: hidden` + 各行 `white-space: nowrap` + 辅助行超宽缩号（下限 2.2mm）；每签 `break-after: page`
- [x] 2.3 A4 双列版式：沿用现有上下结构卡片，码区换 QR 居中
- [x] 2.4 纸型切换：弹窗单选（默认 60×40，`localStorage` 键 `rock_slab_label_paper` 记忆）；专属 `<style>` 元素动态改写 `@page`（60mm 40mm/0 与 A4/8mm）；`break-after: page` 仅 60×40 版式生效
- [x] 2.5 SN 行显隐：序列号非空显示、为空整行不渲染；弹窗常驻「打印时请选择实际大小/100%」提示

## 3. 测试与验证

- [x] 3.1 重写 `AssetPrintDialog.test.ts`：QR 生成调用参数=内部编号（含 ECC M）、SN 显隐两版、纸型切换与记忆、Teleport 与打印输出隔离断言、60×40 源码断言（@page size/break-after/固定高度）
- [x] 3.2 `npm run test` 全量 + `npm run build`（类型门禁）
- [x] 3.3 浏览器实测：`emulateMedia('print')` + `page.pdf(60mm/40mm)` 验证一签一页与内容不越界；A4 双列回归；扫码查询页输入内部编号唯一命中（本地 dev 环境）
