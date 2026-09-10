# 职级修正 leader > manager — 实施任务

## 1. 常量与测试

- [x] 1.1 `constants/index.ts` ROLE_LEVELS：leader:3、manager:4（互换）
- [x] 1.2 `tests/utils/orgTree.test.ts` 排序断言：行政组长排在分公司行政前

## 2. 验证

- [x] 2.1 vitest 全绿 + `npm run build` 类型门通过
- [x] 2.2 组织架构页抽查排序生效（本地手验或以测试为准）
