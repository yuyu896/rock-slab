# 任务：工作台二维码改为移动端盘点入口

## 1. 卡片文案与指向

- [x] 1.1 InstallQrCard.vue：标题改「移动端盘点」，主文案改「微信扫码使用移动端进行盘点」，提示行改「首次使用需登录，登录后选择盘点任务」，删除全部安装话术；文件头注释标注盘点入口语义（组件名不改，见 design 决策 3）
- [x] 1.2 InstallQrCard.vue：二维码内容与展示的 URL 由 `/install` 改为 `/mobile/inventory`（保持 location.origin 运行时生成）

## 2. 测试与验证

- [x] 2.1 更新 InstallQrCard.test.ts：断言新文案（含「安装」字样不出现）、二维码内容为 origin + /mobile/inventory
- [x] 2.2 全量 vitest 通过 + npm run build（类型门禁）通过
- [x] 2.3 手验收口：本地起服务，手机微信扫工作台二维码，确认落在登录页且带 redirect=/mobile/inventory，登录后进盘点任务列表（2026-09-19 用户真机验收通过）
