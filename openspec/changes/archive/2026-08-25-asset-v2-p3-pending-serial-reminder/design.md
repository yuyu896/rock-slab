## Context

设计书第九节 P3 行"待补录提醒"。摸底结论：待补录的判定（序列号空串）、序列化标志（待补录字段）、筛选（`pending_serial=1`）、补录（supplement 端点，`manage_instances` 门禁）全部现成；notifications app 的通知方案需要解决"提醒给谁"（实例场景无明确责任人，只有权限持有者集合可推导）与 notification_type choices 扩展两个决定，成本高且语义牵强。侧边栏已有"资产盘点"动态徽标先例（SidebarNav onMounted 拉 count，spec dynamic-inventory-badge），是现成的轻量被动通道。

## Goals / Non-Goals

**Goals:**
- 采购生成实例后，待补录事实对相关用户可见（徽标），一步进入实例档案页筛选补录。
- 徽标计数尊重数据范围（走 DataScope 的列表接口，各看各的）。

**Non-Goals:**
- 通知/定时提醒（无责任人语义，不扩 notification_type；将来有真实需求再议）。
- 实例档案页改造（"仅看待补录"筛选与补录闭环已完备，不改）。
- 品目字典页/台账页的额外提示位（一个通道足够，避免提醒噪音）。

## Decisions

**D1 徽标挂"实例档案"子项，而非"库存"组父级**
待补录是实例档案的事实时，挂子项语义精确、点击直达页面（父级点击只是展开/收起）。子项此前无徽标渲染，模板在 `nav-submenu-item` 内补一个与 `.nav-badge` 同款式的 span——样式复用，不新增视觉语言。

**D2 计数走既有实例列表接口，不新增 count 端点**
`getFixedAssets({ pending_serial: '1', pageSize: 1 })` 取 `count`，与盘点徽标（`getInventoryTasks({status, pageSize:1})`）同构。DataScope 在 FixedAssetViewSet 生效，徽标数字即浏览者范围内待补录数，无需额外权限判断；无权看到实例的人自然拿不到非零计数。

**D3 onMounted 拉一次，不轮询不订阅**
与盘点徽标行为一致：进系统时反映当时的待补录量，补录完成后下次进入系统刷新。轮询/实时推送对"渐进补录不阻塞"的场景是过度设计。

## Risks / Trade-offs

- [侧边栏收起时子菜单隐藏，徽标不可见] → 与既有子菜单行为一致；展开即见。不为收起态做父级汇总徽标（两个来源将来会打架）。
- [多一次列表请求] → pageSize=1 单查询，成本可忽略；失败静默为 0（同盘点徽标 catch 分支）。

## Migration Plan

纯前端改动，无迁移。回滚还原组件即可。

## Open Questions

无。
