# 标签打印弹窗缺陷修复 — 实施任务

## 1. 纸型切换缩号时序修复（Bug 1）

- [x] 1.1 `AssetPrintDialog.vue` 的 `switchPaper` 改 async：`paper.value` 赋值后 `await nextTick()` 再调 `fitLabelLines()`（localStorage 与 `applyPageSize` 顺序不变）
- [x] 1.2 防回归测试：断言切纸型后 fit 在 DOM class 更新之后执行（源码断言 `switchPaper` 含 `await nextTick`；jsdom 下 stub `getComputedStyle`/`scrollWidth` 验证缩号读的是新纸型字号）

## 2. 导出图片失败可见化（问题 2）

- [x] 2.1 `AssetPrintDialog.vue` 新增 `exportError` ref；`openExport` 的 catch 不再静默弹回（移除 `exportMode.value = false`），置错误态并 `console.error('标签图片导出失败', error)`
- [x] 2.2 导出视图渲染失败占位（中性文案 + 重试按钮复用 `openExport`），复测 `exporting` 态下按钮禁用逻辑
- [x] 2.3 测试：mock `renderLabelDataUrl` reject → 断言停留在导出视图、展示失败提示、console.error 被调用、重试后成功恢复

## 3. 空内部编号导出兜底（问题 3）

- [x] 3.1 `labelImage.ts`：`LabelAssetShape` 加可选 `id`；`labelFileName` 内部编号为空时回退 `标签_未编号_${id.slice(0, 8)}.png`
- [x] 3.2 `AssetPrintDialog.vue`：`exportItems` 结构扩为 `{ id, url, name }`（id 取自 asset），`v-for :key` 改用 `item.id`；`openExport` 传入含 id 的 shape
- [x] 3.3 测试：labelImage 空编号文件名回退用例 + 弹窗导出列表以 id 为键（两个空编号实例不冲突）

## 4. 验证与收口

- [x] 4.1 全量前端测试 `npm run test` 通过
- [x] 4.2 类型门禁 `npm run build` 通过（vitest 不查类型）
- [x] 4.3 手验清单：A4↔60×40 来回切换后打印长品名不截断；导出视图正常路径回归；按用户惯例本地手验后另行部署
