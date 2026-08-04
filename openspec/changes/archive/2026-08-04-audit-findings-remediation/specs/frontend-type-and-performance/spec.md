## ADDED Requirements

### Requirement: 前端核心模型必须强类型化

固定资产等核心业务模型 MUST 有对应的 TypeScript interface（对照后端 `FixedAssetSerializer` 字段），API 调用与 store / 组件中的相关变量 MUST 使用该类型，不得用 `any` / `Record<string, any>` 退化类型保护。

#### Scenario: 固定资产列表与编辑具备类型保护
- **WHEN** 开发者在 `FixedAssetList.vue` 或其 store 中访问固定资产字段
- **THEN** 该变量类型为 `FixedAsset`（或其数组），缺失字段在编译期被类型检查捕获

### Requirement: 金额格式化必须容错字符串型数值

`formatMoney` MUST 接受 DRF `DecimalField` 序列化输出的字符串（如 `"99.50"`）并在入口处 `Number()` 强转、对 NaN 兜底为 0；不得依赖字符串比较或 `String.toLocaleString` 的选项参数。

#### Scenario: 字符串金额被正确格式化
- **WHEN** 资产单价 / 采购金额以字符串 `"99.50"` 传入 `formatMoney`
- **THEN** 输出按人民币正确格式化（如 `¥99.50`），不返回原串或异常精度

### Requirement: 超大前端依赖必须按需懒加载

仅在导入 / 导出等特定场景使用的大型依赖（`exceljs`）MUST 通过动态 `import()` 懒加载，不得进入首屏 bundle；无引用且含已知漏洞的依赖（`xlsx@0.18.5`）MUST 从 `package.json` 移除。

#### Scenario: 首屏 bundle 不含导入导出大依赖
- **WHEN** 构建生产包并检查入口 chunk
- **THEN** `exceljs` 不在首屏 chunk 中（仅在被使用时按需加载），`xlsx` 不出现在任何产物中
