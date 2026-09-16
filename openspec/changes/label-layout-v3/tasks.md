# 任务：标签版式 V3（英文字段前缀）

## 1. 渲染工具（utils/labelImage.ts）

- [x] 1.1 `LABEL_SPEC` 增 `prefixes` 常量（NO./SN:/ITEM/BRANCH/VENDOR/DATE）与首行主码字号 3.4mm；`LabelLine` 泛化为 segments（text/sizeMm/weight/mono/color）
- [x] 1.2 `buildLabelLines` 改五行英文前缀行集（删品目编号行；SN 空隐藏；VENDOR/DATE 同行、单项空只留存在项）
- [x] 1.3 `fitLines` 按段聚合宽度缩号；绘制按段累进 x（首行前缀 2.6mm + 主码 3.4mm 粗）

## 2. 弹窗模板（AssetPrintDialog.vue）

- [x] 2.1 文案行改五行为前缀+值结构（`<span class="label-prefix">` + 值），60×40 与 A4 两版式同步；前缀样式（辅助级字号、灰色）

## 3. 测试与验证

- [x] 3.1 `labelImage.test.ts`：五行集与前缀、空值形态、段式缩号、混合字号几何断言
- [x] 3.2 `AssetPrintDialog.test.ts`：文案断言改五行英文前缀（品目编号行不存在、前缀 span 存在）
- [x] 3.3 `npm run test` 全量 + `npm run build`（类型门禁）
- [x] 3.4 浏览器实测：五行前缀版式、首行混合字号、导出 PNG 与打印预览一致、本地小熊/今日日期数据上目视（本地 dev 环境）
