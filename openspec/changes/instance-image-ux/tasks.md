# 实例图片 UX 修正 — 实施任务

## 1. 行分割线对齐

- [x] 1.1 `FixedAssetList.vue`：`.action-col` 去掉 `display: flex`，改 `white-space: nowrap`；`.action-btn` 改 `display: inline-flex` + `vertical-align: middle` + `margin-right: var(--space-1)`（末钮间距无碍则不特判）
- [x] 1.2 vitest 补一条：挂图行操作列 td 不携带破坏表格布局的 display（可断言渲染后 td 的 computed 类/样式，或退化为快照断言类名不变而样式定义已改——以可测的口径实现）

## 2. 弹窗成功即关

- [x] 2.1 `uploadImage` 成功分支：更新行数据后 `imaging.value = null` 关闭弹窗（成功提示与就地更新保留）
- [x] 2.2 `handleDeleteImage` 成功分支：同上关闭；失败路径确认停留
- [x] 2.3 vitest 补一条：上传成功后弹窗关闭（mock uploadFixedAssetImage 成功，断言 imaging 状态/弹窗消失）

## 3. 验证与收尾

- [x] 3.1 `npm run build` 类型门通过；vitest 全绿
- [x] 3.2 本地浏览器手验：挂图行分割线连续；上传/更换/删除成功即关、失败停留；操作按钮排布与居中不回归
