# 实例盘点 Excel 模板与导入 — 实施任务

## 1. 后端

- [x] 1.1 `download_template` 实例盘分支：清单快照模板（序号/内部编号/序列号/品目编号/品目名称/使用人/所属部门/核对结果/备注），移除 400 拦截
- [x] 1.2 `import_result` 实例盘分支：in_progress 护栏 + Excel 校验复用；按内部编号匹配，「已找到」→matched /「未找到」→missing（check_count+1、核对人/时间、备注），行级错误收集
- [x] 1.3 后端测试：模板含快照行；导入回写 matched/missing；非法值/不在清单行级报错；非 in_progress 拒绝

## 2. 前端

- [x] 2.1 `InventoryTaskList.vue` 下载/导入按钮去掉实例盘隐藏条件

## 3. 验证

- [x] 3.1 全量 pytest；`npm run build` + vitest 全绿
- [x] 3.2 浏览器手验：实例盘任务下载模板（含清单）→ 本地填结果 → 导入回写 → 报告反映
