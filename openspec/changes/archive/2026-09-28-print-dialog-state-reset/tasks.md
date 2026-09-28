# 打印弹窗关闭复位导出会话 — 实施任务

## 1. 状态复位与在途作废

- [x] 1.1 `AssetPrintDialog.vue`：`watch(visible)` 加关闭分支——递增导出会话序号并复位 `exportMode`/`exportItems`/`exportError`/`exporting`
- [x] 1.2 `openExport` 引入会话序号守卫：resolve 过期不写 `exportItems`、catch 过期不置 `exportError`、finally 过期不动 `exporting`

## 2. 测试守护

- [x] 2.1 用例：导出视图关闭弹窗→重开，回到打印预览、无导出态残留
- [x] 2.2 用例：导出在途时关闭弹窗，旧渲染结果不写入、不干扰新一轮导出（渲染中提示不被旧会话关掉、新会话结果正确落地）
- [x] 2.3 全量前端测试 `npm run test` 通过
- [x] 2.4 类型门禁 `npm run build` 通过

## 3. 收口

- [x] 3.1 手验清单：导出视图关闭→重开回打印预览；大批量导出中途关闭→重开再导出正常；纸型记忆仍生效（有意设计）
