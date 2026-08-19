# 磐盘 (Rock Slab) - 分公司资产管理系统

## 系统概述

**磐盘**是一款面向公司行政部门的资产管理系统，用于统一管理各分公司的各类资产，实现资产的全生命周期管理。

### 核心目标

- 集中管理各分公司资产信息
- 追踪资产的分配、调拨、使用状态
- 支持定期盘点与审计
- 提供资产统计与报表分析

---

## 用户角色

| 角色 | 层级 | 管人 | 管资产 | 审批 |
|------|------|------|--------|------|
| 超级管理员 | L1 | 全部用户 | 全部分公司 | 全部 |
| 行政经理 | L2 | - | 查看所有分公司报表 | 集团级审批 |
| 行政主管 | L3 | 区域内的组长/专员 | 区域内所有分公司 | 审批区域内单据 |
| 行政组长 | L4 | 管辖多个分公司的专员 | 仅自己所属分公司 | 无 |
| 行政专员 | L5 | 无 | 仅自己所属分公司 | 无 |

### 组织架构

```
集团
└── 行政经理
    ├── 区域A（行政主管A）
    │   ├── 行政组长1
    │   │   ├── 分公司1（行政专员a）
    │   │   └── 分公司2（行政专员b）
    │   └── 行政组长2
    │       ├── 分公司3（行政专员c）
    │       └── 分公司4（行政专员d）
    ├── 区域B（行政主管B）
    │   └── ...
    └── ...
```

### 职责说明

- **行政经理**：查看全集团资产报表，接收审批抄送，负责集团级资产管理决策
- **行政主管**：管理一个区域内所有分公司的资产，审批下属提交的单据
- **行政组长**：管辖多个分公司的行政专员（人员管理），但只管理自己所属分公司的资产
- **行政专员**：负责本公司的资产管理，创建采购入库、出库、盘点单据，提交主管审批

---

## 核心功能模块

### 1. 组织架构 (Organization)

- **区域管理**：创建/编辑/删除区域，指定区域负责人（行政主管）
- **分公司管理**：创建/编辑/删除分公司，分配所属区域，维护分公司信息（名称、地址、负责人、联系方式）
- **人员管理**：创建/编辑/删除用户，分配角色、所属分公司/区域、上下级关系
- **组织架构图**：可视化展示集团-区域-分公司-人员的层级关系
- **状态管理**：分公司/人员的启用/停用状态

### 2. 资产分类 (Category)

#### 资产类目（一级分类）

| 资产类目 | 物品分类（二级） |
|----------|------------------|
| 固定资产类 | 办公设备、电子设备、家具设施、IT基础设施 |
| 低值易耗品类 | 办公耗材、清洁用品、装饰耗材、设备耗材 |
| 无形资产类 | 软件与数据、知识产权、数字资产 |
| 文档资料类 | 行政文件、技术文档、客户资料 |
| 特殊设备类 | 安防设备、创意工具 |
| 其他资产 | 其他、维修备件 |

#### 功能说明
- **分类管理**：创建/编辑/删除一二级分类
- **分类属性**：不同分类可配置不同的属性字段（如电脑配置CPU/内存，办公桌配置尺寸/材质）
- **警戒线设置**：按分类设置库存警戒数量
- **模板导入**：支持按模板批量导入资产分类数据（Excel格式）

#### 权限说明
- **行政主管及以上**：可新增、编辑、删除分类，可修改资产编号
- **行政组长/行政专员**：仅可查看，不可修改

### 3. 资产管理 (Asset)

> **说明**：本模块为只读/查询视图，资产信息通过【资产流转】模块的单据流转自动更新，不在此直接录入或编辑。

#### 资产信息字段

| 字段 | 说明 |
|------|------|
| 序号 | 自动生成序号 |
| 分公司 | 所属分公司 |
| 资产编号 | 根据分类自动生成，支持手动修改，唯一标识 |
| 资产类目 | 一级分类（固定资产类/低值易耗品类/无形资产类/文档资料类/特殊设备类/其他资产） |
| 物品分类 | 二级分类（办公设备/电子设备/家具设施/IT基础设施等） |
| 资产名称 | 资产名称 |
| 规格 | 资产规格型号 |
| 供应商 | 供应商名称 |
| 采购方式 | 自购/租用 |
| 数量 | 资产数量 |
| 单价 | 单件价格 |
| 购入金额 | 总金额（数量×单价） |
| 入库日期 | 资产入库时间 |
| 出库日期 | 资产出库时间（领用时） |
| 所属部门 | 使用部门 |
| 使用人 | 资产使用人 |
| 当前状态 | 使用中/在库/维修中/报废 |
| 警戒线 | 库存警戒数量 |
| 是否充足 | 充足/不足（对比数量与警戒线） |
| 图片 | 资产照片 |
| 备注 | 其他说明 |

#### 功能说明
- **资产查询**：按分公司/分类/状态等多维度筛选
- **资产详情**：查看资产完整信息
- **资产导出**：支持按分公司导出数据（Excel格式）
- **资产标签**：一维码（Code128），内容为资产编号，系统生成支持打印

#### 资产编号规则
编号格式：`[资产类目代码]-[物品分类代码][5位序号]`

| 资产类目 | 代码 | 物品分类 | 代码 | 示例编号 |
|----------|------|----------|------|----------|
| 固定资产类 | A | 办公设备 | a | A-a00001 |
| 固定资产类 | A | 电子设备 | b | A-b00001 |
| 低值易耗品类 | B | 清洁用品 | c | B-c00001 |
| 无形资产类 | C | 软件与数据 | d | C-d00001 |
| 文档资料类 | D | 行政文件 | e | D-e00001 |
| 特殊设备类 | E | 安防设备 | f | E-f00001 |
| 其他资产 | F | 其他 | g | F-g00001 |

> 编号在分类创建时预设，新增资产时自动继承分类编号前缀并递增序号，支持手动修改

### 4. 资产流转 (Transfer)

#### 采购入库
- **流程**：员工提交采购入库单 → 行政主管审批 → 抄送行政经理 → 审批通过确认入库 → 库存增加、资产信息更新
- **资产编号**：必填，必须选择资产分类中已存在的资产编号
- **模板导入**：支持按模板批量导入采购入库单（Excel格式）
- **权限**：行政专员/行政组长可提交，行政主管审批

#### 领用出库
- **流程**：员工提交领用出库单 → 行政主管审批 → 抄送行政经理 → 审批通过确认出库 → 库存减少、资产信息更新
- **模板导入**：支持按模板批量导入领用出库单（Excel格式）
- **权限**：行政专员/行政组长可提交，行政主管审批

#### 调拨
- **流程**：员工提交调拨单 → 行政主管审批 → 抄送行政经理 → 审批通过 → 资产所属分公司变更
- **模板导入**：支持按模板批量导入调拨单（Excel格式）
- **权限**：行政专员/行政组长可提交，行政主管审批

#### 维修
- **流程**：员工提交维修单 → 行政主管审批 → 抄送行政经理 → 资产状态变更为"维修中" → 维修完成后归还 → 状态恢复
- **权限**：行政专员/行政组长可提交，行政主管审批

#### 报废
- **流程**：员工提交报废单 → 行政主管审批 → 抄送行政经理 → 审批通过 → 资产状态变更为"报废"
- **权限**：行政专员/行政组长可提交，行政主管审批

> **说明**：行政经理仅接收抄送供查看，不参与审批，不影响流程运转

#### 审批流程
```
行政专员/行政组长提交 → 行政主管审批 → 抄送行政经理（审批通过即生效）
```

### 5. 资产盘点 (Inventory)

#### 盘点任务状态流转

```
待盘点 → 盘点中 → 待审核 → 已完成 / 已驳回 / 已作废
                              ↓
                           重新盘点 → 待审核
```

| 状态 | 说明 |
|------|------|
| **待盘点** | 任务已创建，尚未开始 |
| **盘点中** | 正在执行盘点，支持多人协作 |
| **待审核** | 盘点完成，提交审批中 |
| **已完成** | 审批通过，库存已调整 |
| **已驳回** | 审批驳回，需重新盘点 |
| **已作废** | 任务取消/过期作废 |

#### 盘点流程
1. **创建盘点任务**：所有角色均可创建盘点任务（按分公司/分类/全部）
2. **开始盘点**：任务状态变更为"盘点中"，可多人同时协作盘点
3. **执行盘点**：行政专员/组长扫码或手动录入盘点数据
4. **完成盘点**：所有物品盘点完成后，提交审批，状态变更为"待审核"
5. **审批盘点结果**：行政主管审批盘点报告
   - **通过**：状态变更为"已完成"，系统自动调整库存
   - **驳回**：状态变更为"已驳回"，需重新盘点后再次提交
6. **重新盘点**：驳回后可重新执行盘点，完成后再次提交审批

> **重要**：盘点结果需行政主管审批通过后，库存才会变动

#### 盘点结果说明

| 结果 | 说明 | 处理方式 |
|------|------|----------|
| **已盘点-正常** | 实际数量与账面一致 | 无需调整 |
| **盘盈** | 实际数量大于账面 | 审批通过后增加库存 |
| **盘亏** | 实际数量小于账面 | 审批通过后减少库存 |
| **未盘点** | 账面有但实际未扫码/录入 | 根据漏盘规则处理 |

#### 漏盘规则（系统配置）

| 规则 | 说明 |
|------|------|
| **保持不变** | 漏盘物品库存数量不变（默认） |
| **清零处理** | 漏盘物品库存数量清零 |

> 管理员可在系统设置中配置默认漏盘规则，创建盘点任务时可选覆盖

#### 重复盘点规则

| 规则 | 说明 |
|------|------|
| **累计数量** | 同一物品多次盘点，数量累加 |
| **以最后一次为准** | 同一物品多次盘点，以最后一次数据为准（默认） |

> 创建盘点任务时可选择重复盘点规则

#### 多人协作盘点
- 同一盘点任务支持多人同时扫码/录入
- 实时同步盘点进度
- 显示各盘点人已盘数量
- 避免重复盘点冲突

#### 功能说明
- **盘点任务管理**：创建、查看、删除、作废盘点任务
- **盘点执行**：扫码盘点、手动录入、多人协作
- **盘点进度**：实时显示已盘点/未盘点数量、各盘点人进度
- **盘点报告**：差异明细、盘盈盘亏统计、未盘点清单
- **盘点审批**：行政主管审批盘点结果，支持通过/驳回
- **重新盘点**：驳回后可重新执行盘点并再次提交

### 6. 移动端 (Mobile)

- **盘点扫码**：使用手机扫描一维码进行盘点
- **资产查询**：扫码或搜索查看资产详情
- **单据提交**：手机上提交入库/出库单
- **移动审批**：主管在手机上审批单据
- **消息通知**：接收审批提醒、任务通知

> **标签码方案**：一维码（Code128），内容为资产编号，系统生成支持打印

### 7. 可视化看板 (Dashboard)

- **资产库存监测**：实时展示资产库存数量、状态分布
- **多维度统计图表**：按分类、分公司、状态等维度展示
- **待办提醒**：待审批、待盘点等任务提醒
- **角色权限视图**：
  - 超级管理员/行政经理：全集团数据看板
  - 行政主管：管辖区域内分公司数据看板
  - 行政组长/行政专员：所属分公司数据看板

### 8. 统计报表 (Reports)

- 资产总览（数量、价值统计）
- 分公司资产分布
- 资产状态分析
- 资产变动明细

---

## 数据模型

### Region (区域)

```
Region {
  id: string (UUID)
  name: string              // 区域名称
  code: string              // 区域编码
  managerId: string         // 负责人ID（行政主管）
  status: enum (active, inactive)
  createdAt: datetime
  updatedAt: datetime
}
```

### Branch (分公司)

```
Branch {
  id: string (UUID)
  name: string              // 分公司名称
  code: string              // 分公司编码
  regionId: string          // 所属区域ID
  address: string           // 地址
  managerId: string?        // 负责人ID
  phone: string?            // 联系电话
  status: enum (active, inactive)
  createdAt: datetime
  updatedAt: datetime
}
```

### Category (资产分类)

```
Category {
  id: string (UUID)
  assetCategory: string     // 资产类目（一级分类）
  itemCategory: string      // 物品分类（二级分类）
  assetName: string         // 资产名称
  assetCode: string         // 资产编号
  unit: string              // 计量单位
  warningLine: number?      // 警戒线
  remarks: string?          // 备注
  createdAt: datetime
  updatedAt: datetime
}
```

### Asset (资产)

```
Asset {
  id: string (UUID)
  序号: number              // 自动生成序号
  分公司: string            // 分公司名称
  资产编号: string          // 资产编号（唯一）
  分公司编号: string        // 分公司编码
  资产类目: string          // 一级分类
  电脑序列号: string?       // 电脑序列号（电子设备专用）
  供应商: string?           // 供应商名称
  物品分类: string          // 二级分类
  资产名称: string          // 资产名称
  图片: string?             // 图片URL
  入库日期: date?           // 入库时间
  是否租用: boolean         // 是否租用
  数量: number              // 资产数量
  规格: string?             // 规格型号
  单价: number?             // 单价
  购入金额: number?         // 总金额（数量×单价）
  出库日期: date?           // 出库时间
  所属部门: string?         // 使用部门
  使用人: string?           // 使用人
  当前状态: enum (在库, 使用中, 维修中, 报废)
  警戒线: number?           // 库存警戒数量
  是否充足: boolean?        // 充足/不足（对比数量与警戒线）
  备注: string?             // 其他说明
  createdAt: datetime
  updatedAt: datetime
}
```

### User (用户)

```
User {
  id: string (UUID)
  phone: string             // 手机号（登录账号，唯一）
  name: string              // 姓名
  branchId: string?         // 所属分公司
  regionId: string?         // 所属区域（行政主管必填）
  leaderId: string?         // 直属上级ID（专员→组长→主管→经理）
  role: enum (admin, manager, supervisor, leader, staff)
          // admin=超级管理员, manager=行政经理, supervisor=行政主管
          // leader=行政组长, staff=行政专员
  status: enum (active, inactive)
  createdBy: string?        // 创建人ID（管理员）
  createdAt: datetime
  updatedAt: datetime
}
```

> **认证方式**：手机号 + 密码登录，账号由系统管理员统一创建

### Transfer (调拨记录)

```
Transfer {
  id: string (UUID)
  调拨日期: date             // 调拨日期
  调出分公司: string?        // 分公司(调出)
  调出部门: string?          // 调出部门（可选）
  调入分公司: string?        // 调入分公司
  调入部门: string?          // 调入部门（可选）
  资产编号: string           // 资产编号
  资产名称: string           // 资产名称
  规格型号: string?          // 规格型号
  调拨数量: number           // 调拨数量
  调拨原因: string?          // 调拨原因
  调出负责人: string?        // 调出负责人
  调入负责人: string?        // 调入负责人
  备注: string?              // 备注
  审批状态: enum (待审批, 已通过, 已驳回)
  审批人: string?            // 审批人ID
  审批时间: datetime?        // 审批时间
  创建人: string             // 创建人ID
  createdAt: datetime
  updatedAt: datetime
}
```

### InventoryTask (盘点任务)

```
InventoryTask {
  id: string (UUID)
  name: string              // 任务名称
  branchId: string?         // 盘点分公司（null为全部）
  categoryId: string?       // 盘点分类（null为全部）
  status: enum (pending, in_progress, pending_review, completed, rejected, cancelled)
            // pending=待盘点, in_progress=盘点中, pending_review=待审核
            // completed=已完成, rejected=已驳回, cancelled=已作废
  missedRule: enum (keep, zero)  // 漏盘规则：keep=保持不变, zero=清零
  repeatRule: enum (last, accumulate)  // 重复盘点规则：last=以最后一次为准, accumulate=累计
  createdBy: string         // 创建人ID
  startedAt: datetime?      // 开始时间
  submittedAt: datetime?    // 提交审批时间
  completedAt: datetime?    // 完成时间
  rejectedAt: datetime?     // 驳回时间
  rejectedBy: string?       // 驳回人ID
  rejectReason: string?     // 驳回原因
  createdAt: datetime
  updatedAt: datetime
}
```

### InventoryItem (盘点明细)

```
InventoryItem {
  id: string (UUID)
  taskId: string            // 盘点任务ID
  assetId: string           // 资产ID
  expectedQty: number       // 账面数量
  actualQty: number?        // 实际盘点数量
  result: enum (matched, surplus, missing, unchecked)
            // matched=正常, surplus=盘盈, missing=盘亏, unchecked=未盘点
  checkCount: number        // 盘点次数（支持重复盘点）
  checkedBy: string?        // 最后盘点人ID
  checkedAt: datetime?      // 最后盘点时间
  remarks: string?          // 备注
  createdAt: datetime
  updatedAt: datetime
}
```

### InventoryCheck (盘点记录)

```
InventoryCheck {
  id: string (UUID)
  taskId: string            // 盘点任务ID
  itemId: string            // 盘点明细ID
  assetId: string           // 资产ID
  qty: number               // 本次盘点数量
  checkedBy: string         // 盘点人ID
  checkedAt: datetime       // 盘点时间
  device: string?           // 设备信息（PC/手机）
}
```

> **说明**：InventoryCheck 记录每次盘点操作，支持同一物品多次盘点和多人协作盘点

---

## API 端点设计

### 认证与用户

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | /api/auth/login | 手机号密码登录 |
| POST | /api/auth/logout | 退出登录 |
| GET | /api/auth/profile | 获取当前用户信息 |
| PUT | /api/auth/password | 修改密码 |
| GET | /api/users | 获取用户列表（管理员） |
| POST | /api/users | 创建用户（管理员） |
| PUT | /api/users/:id | 更新用户（管理员） |
| DELETE | /api/users/:id | 停用用户（管理员） |

### 分公司管理

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | /api/branches | 获取分公司列表（树形） |
| GET | /api/branches/:id | 获取分公司详情 |
| POST | /api/branches | 创建分公司 |
| PUT | /api/branches/:id | 更新分公司 |
| DELETE | /api/branches/:id | 删除分公司 |

### 资产分类

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | /api/categories | 获取分类树 |
| GET | /api/categories/:id | 获取分类详情 |
| POST | /api/categories | 创建分类 |
| PUT | /api/categories/:id | 更新分类 |
| DELETE | /api/categories/:id | 删除分类 |

### 资产管理

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | /api/assets | 获取资产列表（支持筛选分页） |
| GET | /api/assets/:id | 获取资产详情 |
| POST | /api/assets | 创建资产 |
| PUT | /api/assets/:id | 更新资产 |
| DELETE | /api/assets/:id | 删除资产 |
| POST | /api/assets/import | 批量导入资产 |
| GET | /api/assets/export | 导出资产 |

### 资产流转

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | /api/transfers | 获取流转记录列表 |
| GET | /api/transfers/:id | 获取流转详情 |
| POST | /api/transfers/assign | 资产领用 |
| POST | /api/transfers/return | 资产归还 |
| POST | /api/transfers/transfer | 资产调拨 |
| POST | /api/transfers/repair | 资产维修 |
| POST | /api/transfers/scrap | 资产报废 |
| POST | /api/transfers/:id/approve | 审批流转 |

### 盘点管理

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | /api/inventories | 获取盘点任务列表 |
| GET | /api/inventories/:id | 获取盘点任务详情 |
| POST | /api/inventories | 创建盘点任务 |
| POST | /api/inventories/:id/start | 开始盘点 |
| POST | /api/inventories/:id/check | 盘点确认（逐项） |
| POST | /api/inventories/:id/submit | 提交审批 |
| POST | /api/inventories/:id/approve | 审批通过 |
| POST | /api/inventories/:id/reject | 审批驳回 |
| POST | /api/inventories/:id/recount | 重新盘点（驳回后） |
| POST | /api/inventories/:id/cancel | 作废盘点任务 |
| GET | /api/inventories/:id/report | 获取盘点报告 |
| GET | /api/inventories/:id/progress | 获取盘点进度 |
| GET | /api/inventories/:id/checks | 获取盘点记录（多人协作） |

### 统计报表

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | /api/reports/overview | 资产总览统计 |
| GET | /api/reports/by-branch | 分公司资产分布 |
| GET | /api/reports/by-status | 资产状态分析 |
| GET | /api/reports/transfers | 变动明细 |

---

## 技术栈

### 后端
- **框架**: Django 5.x + Django REST Framework
- **数据库**: PostgreSQL / MySQL
- **缓存**: Redis
- **文件存储**: MinIO / OSS
- **认证**: Django 内置认证 / JWT

### 前端
- **框架**: Vue 3 + TypeScript
- **构建工具**: Vite
- **UI库**: Element Plus
- **状态管理**: Pinia
- **HTTP客户端**: Axios

### 部署
- **容器化**: Docker + Docker Compose
- **反向代理**: Nginx

---

## 开发阶段规划

### Phase 1: 基础功能 (MVP)
- [ ] 用户认证与授权
- [ ] 分公司管理
- [ ] 资产分类管理
- [ ] 资产 CRUD
- [ ] 资产列表与搜索

### Phase 2: 资产流转
- [ ] 资产领用/归还
- [ ] 分公司间调拨
- [ ] 审批流程

### Phase 3: 盘点与报表
- [ ] 盘点任务管理
- [ ] 盘点执行
- [ ] 统计报表

### Phase 4: 增强功能
- [ ] 资产导入导出
- [ ] 资产照片管理
- [ ] 资产标签打印（二维码）
- [ ] 消息通知
- [ ] 操作日志

---

## 待确认问题

1. ~~**技术栈偏好**~~: ✅ Django + Vue3
2. ~~**认证方式**~~: ✅ 独立认证，手机号登录，管理员创建账号
3. ~~**数据量级**~~: ✅ 资产分类380+，分公司50→100家，资产预计10万+
4. ~~**审批流程**~~: ✅ 行政专员/组长提交 → 行政主管审批 → 抄送行政经理
5. ~~**移动端**~~: ✅ 盘点扫码、资产查询、单据提交、移动审批、消息通知
6. ~~**集成需求**~~: ✅ 暂无，预留接口供后续接入办公系统
