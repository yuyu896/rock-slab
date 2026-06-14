## ADDED Requirements

### Requirement: 移除维修(repair)和报废(scrap)操作类型
系统 SHALL 不再支持维修和报废两种流转操作，相关前后端代码全部删除。

#### Scenario: 后端不再暴露 repair/scrap 端点
- **WHEN** 客户端请求 `POST /api/transfers/repair/` 或 `POST /api/transfers/scrap/`
- **THEN** 返回 404

#### Scenario: 前端不再显示维修/报废选项
- **WHEN** 用户查看流转操作的类型选项
- **THEN** 只显示采购入库、领用、归还、调拨，不显示维修和报废

#### Scenario: 历史数据保留
- **WHEN** 数据库中已存在 action_type 为 repair 或 scrap 的 Transfer 记录
- **THEN** 这些记录不受影响，仍可通过列表查询查看
