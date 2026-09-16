# 任务：标签版式调整 V2

## 1. 数据与渲染工具

- [x] 1.1 `FixedAssetList.toPrintShape` 补传 `供应商: item.供应商 || ''`、`采购日期: item.采购日期 || ''`
- [x] 1.2 `utils/labelImage.ts`：`LABEL_SPEC` 字号上调（3.6/3.0/3.4/2.6）、行距 0.5、行高系数 1.2、新增 `blockLiftMm: 0.4`；`buildLabelLines` 改六行集（品目编号、分公司分行；供应商·采购日期合并行、空值隐藏）；布局计算加居中后上移 0.4mm

## 2. 弹窗版式（AssetPrintDialog.vue）

- [x] 2.1 60×40 打印版式：文案改六行（分公司独立行 + 供应商·采购日期行，空值 v-if 隐藏）、字号/行距 CSS 与 `LABEL_SPEC` 同步、垂直居中上移校正
- [x] 2.2 A4 双列版式：同步新增文案行（px 字号不变），空值隐藏规则一致

## 3. 测试与验证

- [x] 3.1 `labelImage.test.ts`：六行集断言（含供应商/采购日期合并行三种空值形态）、新字号/几何断言、上移校正断言
- [x] 3.2 `AssetPrintDialog.test.ts`：文案行断言更新（品目行不含分公司、供应商行显隐）
- [x] 3.3 `npm run test` 全量 + `npm run build`（类型门禁）
- [x] 3.4 浏览器实测：打印预览与导出 PNG 均为六行新字号、目视垂直居中不偏下；A4 版式回归（本地 dev 环境）
