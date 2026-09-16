# 任务：标签导出图片（打印第二通道）

## 1. 渲染工具（utils/labelImage.ts）

- [x] 1.1 新建 `labelImage.ts`：导出 `LABEL_SPEC` 常量（边距/QR 尺寸/字号/颜色，与打印 CSS 同参数）与 `renderLabelCanvas(asset)`——960×640 canvas、QR 用 `qrcode.toCanvas` 画离屏后贴入（ECC M、13mm+2mm 静区）、三区文案 fillText、SN 空跳行、measureText 超宽缩号（下限 2.2mm）
- [x] 1.2 `toDataURL('image/png')` 输出，文件名 `标签_<内部编号>.png`

## 2. 弹窗导出交互（AssetPrintDialog.vue）

- [x] 2.1 弹窗底部新增「导出图片」按钮，点击切换到导出视图：标签 PNG 预览列表 + 顶部「全部下载」+ 每张「下载」
- [x] 2.2 手机长按保存路径：图片以 `<img>` 展示（非 canvas），导出视图注明「App 内请选原尺寸 60×40」
- [x] 2.3 导出视图可返回打印预览；打印通道行为不变

## 3. 测试与验证

- [x] 3.1 `labelImage` 单测：mock canvas/measureText 断言布局参数、SN 空跳行、缩号触发、QR 调用参数（内部编号 + ECC M）
- [x] 3.2 `AssetPrintDialog.test.ts` 扩展：导出按钮出现、导出视图渲染 N 张图、全部下载触发 N 次、文件名含内部编号
- [x] 3.3 `npm run test` 全量 + `npm run build`（类型门禁）
- [x] 3.4 浏览器实测：导出 PNG 尺寸 960×640、肉眼比对与打印版式一致、下载文件可打开、（如有条件）手机浏览器长按保存并用标签机 App 打印一张实物（本地 dev 环境）
