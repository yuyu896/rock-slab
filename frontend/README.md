# 磐盘 (Rock Slab) - 分公司资产管理系统

## 项目概述

**磐盘**是一款面向公司行政部门的资产管理系统，用于统一管理各分公司的各类资产，实现资产的全生命周期管理。

### 核心目标

- 集中管理各分公司资产信息
- 追踪资产的分配、调拨、使用状态
- 支持定期盘点与审计
- 提供资产统计与报表分析

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

## 文件结构

```
frontend/
├── public/                     # 静态资源
│   └── favicon.ico
├── src/
│   ├── assets/                 # 资源文件
│   │   ├── images/            # 图片
│   │   └── fonts/             # 字体
│   ├── components/            # 公共组件
│   │   ├── common/            # 通用组件
│   │   │   ├── Button.vue
│   │   │   ├── Card.vue
│   │   │   ├── Modal.vue
│   │   │   ├── Table.vue
│   │   │   └── Pagination.vue
│   │   ├── layout/            # 布局组件
│   │   │   ├── Sidebar.vue
│   │   │   ├── Header.vue
│   │   │   └── Footer.vue
│   │   └── business/          # 业务组件
│   │       ├── AssetCard.vue
│   │       ├── InventoryProgress.vue
│   │       ├── StatusBadge.vue
│   │       └── CategoryTree.vue
│   ├── layouts/               # 页面布局
│   │   ├── MainLayout.vue     # 主布局（侧边栏+顶部栏）
│   │   └── BlankLayout.vue    # 空白布局
│   ├── views/                 # 页面视图
│   │   ├── Dashboard.vue      # 工作台/仪表盘
│   │   ├── AssetList.vue      # 资产列表
│   │   ├── Inventory.vue      # 资产盘点
│   │   ├── Category.vue       # 资产分类
│   │   ├── Purchase.vue       # 采购入库
│   │   ├── Transfer.vue       # 调拨记录
│   │   ├── Organization.vue   # 组织架构
│   │   ├── Reports.vue        # 统计报表
│   │   └── MobileScan.vue     # 移动端盘点
│   ├── router/                # 路由配置
│   │   └── index.ts
│   ├── store/                 # 状态管理
│   │   ├── index.ts
│   │   ├── modules/
│   │   │   ├── user.ts
│   │   │   ├── asset.ts
│   │   │   └── inventory.ts
│   ├── api/                   # API 接口
│   │   ├── index.ts
│   │   ├── auth.ts
│   │   ├── asset.ts
│   │   ├── category.ts
│   │   ├── inventory.ts
│   │   └── organization.ts
│   ├── utils/                 # 工具函数
│   │   ├── request.ts         # HTTP 请求封装
│   │   ├── format.ts          # 格式化工具
│   │   ├── validate.ts        # 验证工具
│   │   └── storage.ts         # 本地存储
│   ├── hooks/                 # 组合式函数
│   │   ├── useTable.ts
│   │   ├── useForm.ts
│   │   └── usePermission.ts
│   ├── styles/                # 样式文件
│   │   ├── variables.css      # CSS 变量（设计系统）
│   │   ├── reset.css          # 样式重置
│   │   ├── global.css         # 全局样式
│   │   └── animations.css     # 动画样式
│   ├── types/                 # TypeScript 类型
│   │   ├── api.d.ts
│   │   ├── asset.d.ts
│   │   ├── user.d.ts
│   │   └── common.d.ts
│   ├── constants/             # 常量定义
│   │   ├── status.ts
│   │   ├── roles.ts
│   │   └── categories.ts
│   ├── App.vue                # 根组件
│   └── main.ts                # 入口文件
├── .env                       # 环境变量
├── .env.development           # 开发环境变量
├── .env.production            # 生产环境变量
├── index.html                 # HTML 模板
├── package.json               # 依赖配置
├── tsconfig.json              # TypeScript 配置
├── vite.config.ts             # Vite 配置
└── README.md                  # 项目说明
```

---

## 页面说明

### 1. 工作台 (Dashboard)

**路径**: `/dashboard`

**功能**:
- 欢迎区域 + 快捷操作按钮
- 关键指标卡片（资产总数、使用中、待审批、库存不足）
- 资产趋势柱状图（近6个月）
- 分类分布图
- 待办任务列表
- 分公司排行
- 最近动态

### 2. 资产列表 (AssetList)

**路径**: `/assets/list`

**功能**:
- 多条件筛选（分公司/分类/状态/关键词）
- 快捷筛选标签（库存不足、待维修、本月新增）
- 批量操作栏（打印标签、批量调拨、批量报废）
- 数据表格（支持排序、选择、分页）
- 资产详情查看
- 导出功能

### 3. 资产盘点 (Inventory)

**路径**: `/inventory`

**功能**:
- 盘点任务卡片列表
- 任务状态流转（待盘点→盘点中→待审核→已完成/已驳回/已作废）
- 任务详情视图
- 扫码盘点界面
  - 扫码输入框
  - 进度环显示
  - 异常统计
  - 最近盘点记录
- 多人协作支持

### 4. 资产分类 (Category)

**路径**: `/categories`

**功能**:
- 统计卡片（资产类目数、物品分类数、资产种类、库存不足）
- 筛选（关键词搜索、类目筛选）
- 视图切换（表格/卡片）
- 分类编辑弹窗
- 模板导入

### 5. 采购入库 (Purchase)

**路径**: `/assets/purchase`

**功能**:
- 入库单列表
- 新建入库单表单
  - 基本信息（分公司、供应商、采购日期）
  - 物品明细（动态增删）
  - 金额自动计算
- 模板导入
- 审批状态显示

### 6. 调拨记录 (Transfer)

**路径**: `/assets/transfer`

**功能**:
- 调拨记录列表
- 调出/调入信息展示
- 箭头可视化流转方向
- 状态筛选
- 详情查看
- 审批操作

### 7. 组织架构 (Organization)

**路径**: `/organization`

**功能**:
- 标签页切换（区域管理/分公司管理/人员管理）
- 统计卡片
- 区域卡片视图
- 分公司表格视图
- 人员表格视图
- 新增/编辑弹窗

### 8. 统计报表 (Reports)

**路径**: `/reports`

**功能**:
- 核心指标卡片（资产总数、资产总值、使用率、库存不足）
- 分公司资产排行柱状图
- 资产分类分布环形图
- 资产状态分布
- 月度变动趋势图
- 详细报表表格
- 导出功能

### 9. 移动端盘点 (MobileScan)

**路径**: `/mobile/scan`

**功能**:
- 移动端适配布局
- 任务信息显示
- 进度环
- 扫码输入（支持扫码枪）
- 异常统计（盘盈/盘亏）
- 最近扫描记录
- 数量确认弹窗
- 底部操作栏

---

## 用户角色

| 角色 | 层级 | 管人 | 管资产 | 审批 |
|------|------|------|--------|------|
| 超级管理员 | L1 | 全部用户 | 全部分公司 | 全部 |
| 行政经理 | L2 | - | 查看所有分公司报表 | 集团级审批 |
| 行政主管 | L3 | 区域内的组长/专员 | 区域内所有分公司 | 审批区域内单据 |
| 行政组长 | L4 | 管辖多个分公司的专员 | 仅自己所属分公司 | 无 |
| 行政专员 | L5 | 无 | 仅自己所属分公司 | 无 |

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
  是否充足: boolean?        // 充足/不足
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
  status: enum (active, inactive)
  createdBy: string?        // 创建人ID（管理员）
  createdAt: datetime
  updatedAt: datetime
}
```

### Transfer (调拨记录)
```
Transfer {
  id: string (UUID)
  调拨日期: date            // 调拨日期
  调出分公司: string?       // 分公司(调出)
  调出部门: string?         // 调出部门（可选）
  调入分公司: string?       // 调入分公司
  调入部门: string?         // 调入部门（可选）
  资产编号: string          // 资产编号
  资产名称: string          // 资产名称
  规格型号: string?         // 规格型号
  调拨数量: number          // 调拨数量
  调拨原因: string?         // 调拨原因
  调出负责人: string?       // 调出负责人
  调入负责人: string?       // 调入负责人
  备注: string?             // 备注
  审批状态: enum (待审批, 已通过, 已驳回)
  审批人: string?           // 审批人ID
  审批时间: datetime?       // 审批时间
  创建人: string            // 创建人ID
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
  missedRule: enum (keep, zero)     // 漏盘规则
  repeatRule: enum (last, accumulate) // 重复盘点规则
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
  checkCount: number        // 盘点次数
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

---

## 设计系统

### 色彩

**品牌主色 - 温暖的绿色系**
```css
--color-primary-50: oklch(0.98 0.02 145)
--color-primary-100: oklch(0.94 0.04 145)
--color-primary-200: oklch(0.88 0.08 145)
--color-primary-300: oklch(0.78 0.12 145)
--color-primary-400: oklch(0.68 0.16 145)
--color-primary-500: oklch(0.58 0.18 145)  /* 主色 */
--color-primary-600: oklch(0.48 0.16 145)
--color-primary-700: oklch(0.40 0.14 145)
```

**状态色**
- 成功: `oklch(0.65 0.18 145)`
- 警告: `oklch(0.75 0.16 85)`
- 危险: `oklch(0.60 0.20 25)`
- 信息: `oklch(0.60 0.15 240)`

### 字体

- **主字体**: "Noto Sans SC", "PingFang SC", -apple-system, BlinkMacSystemFont
- **等宽字体**: "JetBrains Mono", "Fira Code", monospace

### 间距

```css
--space-1: 0.25rem   /* 4px */
--space-2: 0.5rem    /* 8px */
--space-3: 0.75rem   /* 12px */
--space-4: 1rem      /* 16px */
--space-5: 1.25rem   /* 20px */
--space-6: 1.5rem    /* 24px */
--space-8: 2rem      /* 32px */
```

---

## 开发指南

### 安装依赖
```bash
npm install
```

### 启动开发服务器
```bash
npm run dev
```

### 构建生产版本
```bash
npm run build
```

### 代码规范
```bash
npm run lint
npm run format
```

---

## API 端点

### 认证与用户
| 方法 | 路径 | 描述 |
|------|------|------|
| POST | /api/auth/login | 手机号密码登录 |
| POST | /api/auth/logout | 退出登录 |
| GET | /api/auth/profile | 获取当前用户信息 |
| PUT | /api/auth/password | 修改密码 |

### 资产管理
| 方法 | 路径 | 描述 |
|------|------|------|
| GET | /api/assets | 获取资产列表 |
| GET | /api/assets/:id | 获取资产详情 |
| POST | /api/assets/import | 批量导入资产 |
| GET | /api/assets/export | 导出资产 |

### 盘点管理
| 方法 | 路径 | 描述 |
|------|------|------|
| GET | /api/inventories | 获取盘点任务列表 |
| POST | /api/inventories | 创建盘点任务 |
| POST | /api/inventories/:id/start | 开始盘点 |
| POST | /api/inventories/:id/check | 盘点确认 |
| POST | /api/inventories/:id/submit | 提交审批 |
| POST | /api/inventories/:id/approve | 审批通过 |
| POST | /api/inventories/:id/reject | 审批驳回 |

---

## 版本历史

### v1.0.0 (2026-03-27)
- 初始版本
- 完成核心功能模块设计
- 完成 UI 界面设计
