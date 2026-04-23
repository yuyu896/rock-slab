/* 磐盘 - Rock Slab 类型定义 */

// ============ 枚举 ============

/** 用户角色 */
export const UserRole = {
  ADMIN: 'admin',
  MANAGER: 'manager',
  SUPERVISOR: 'supervisor',
  LEADER: 'leader',
  STAFF: 'staff',
} as const
export type UserRoleType = (typeof UserRole)[keyof typeof UserRole]

/** 资产状态 */
export const AssetStatus = {
  IN_STOCK: '在库',
  IN_USE: '使用中',
  UNDER_REPAIR: '维修中',
  SCRAPPED: '报废',
} as const
export type AssetStatusType = (typeof AssetStatus)[keyof typeof AssetStatus]

/** 审批状态 */
export const ApprovalStatus = {
  PENDING: '待审批',
  APPROVED: '已通过',
  REJECTED: '已驳回',
  WAREHOUSED: '已入库',
} as const
export type ApprovalStatusType = (typeof ApprovalStatus)[keyof typeof ApprovalStatus]

/** 盘点任务状态 */
export const InventoryTaskStatus = {
  PENDING: 'pending',
  IN_PROGRESS: 'in_progress',
  PENDING_REVIEW: 'pending_review',
  COMPLETED: 'completed',
  REJECTED: 'rejected',
  CANCELLED: 'cancelled',
} as const
export type InventoryTaskStatusType = (typeof InventoryTaskStatus)[keyof typeof InventoryTaskStatus]

/** 盘点结果 */
export const InventoryItemResult = {
  MATCHED: 'matched',
  SURPLUS: 'surplus',
  MISSING: 'missing',
  UNCHECKED: 'unchecked',
} as const
export type InventoryItemResultType = (typeof InventoryItemResult)[keyof typeof InventoryItemResult]

/** 实体状态 */
export const EntityStatus = {
  ACTIVE: 'active',
  INACTIVE: 'inactive',
} as const
export type EntityStatusType = (typeof EntityStatus)[keyof typeof EntityStatus]

/** 漏盘规则 */
export const MissedRule = {
  KEEP: 'keep',
  ZERO: 'zero',
} as const
export type MissedRuleType = (typeof MissedRule)[keyof typeof MissedRule]

/** 重复盘点规则 */
export const RepeatRule = {
  LAST: 'last',
  ACCUMULATE: 'accumulate',
} as const
export type RepeatRuleType = (typeof RepeatRule)[keyof typeof RepeatRule]

// ============ 数据接口 ============

/** 区域 */
export interface Region {
  id: string
  name: string
  code: string
  manager: string
  status: EntityStatusType
  createdAt: string
  updatedAt: string
}

/** 分公司 */
export interface Branch {
  id: string
  name: string
  code: string
  region: string
  address: string
  manager?: string
  phone?: string
  status: EntityStatusType
  createdAt: string
  updatedAt: string
}

/** 资产类目 */
export interface Category {
  id?: string
  资产类目: string
  物品分类: string
  资产名称: string
  资产编号: string
  计量单位: string
  警戒线?: number
  备注?: string
  资产数量?: number
  在库数量?: number
  资产总数量?: number
  在库总数量?: number
  createdAt?: string
  updatedAt?: string
}

/** 创建/更新分类的请求体（使用英文字段名） */
export interface CategoryRequest {
  asset_category: string
  item_category: string
  asset_name: string
  asset_code: string
  unit: string
  warning_line?: number | null
  remarks?: string
}

/** 资产 */
export interface Asset {
  id: string
  序号: number
  分公司: string
  分公司编号: string
  branch?: string
  branchName?: string
  资产编号: string
  资产类目: string
  物品分类: string
  资产名称: string
  规格?: string
  供应商?: string
  图片?: string
  入库日期?: string
  是否租用: boolean
  数量: number
  单价?: number
  购入金额?: number
  出库日期?: string
  所属部门?: string
  使用人?: string
  当前状态: AssetStatusType
  警戒线?: number
  是否充足?: boolean
  电脑序列号?: string
  备注?: string
  createdAt: string
  updatedAt: string
}

/** 用户 */
export interface User {
  id: string
  phone: string
  name: string
  branch?: string
  region?: string
  leader?: string
  team?: string
  role: UserRoleType
  status: EntityStatusType
  avatar?: string
  systemAvatar?: string
  createdBy?: string
  createdAt: string
  updatedAt: string
}

/** 行政组 */
export interface Team {
  id: string
  name: string
  region: string
  regionName?: string
  leader?: string
  leaderName?: string
  memberCount?: number
  status: EntityStatusType
  createdAt: string
  updatedAt: string
}

/** 调拨/流转记录 */
export type TransferActionType = 'purchase' | 'assign' | 'return' | 'transfer'

export interface Transfer {
  id: string
  调拨日期: string
  调出分公司?: string
  调出部门?: string
  调入分公司?: string
  调入部门?: string
  from_branch?: string
  to_branch?: string
  fromBranch?: string
  toBranch?: string
  fromBranchName?: string
  toBranchName?: string
  资产编号: string
  资产名称: string
  规格型号?: string
  调拨数量: number
  调拨原因?: string
  调出负责人?: string
  调入负责人?: string
  使用人?: string
  所属部门?: string
  备注?: string
  审批状态: ApprovalStatusType
  审批人?: string
  审批时间?: string
  创建人: string
  action_type?: TransferActionType
  createdAt: string
  updatedAt: string
}

/** 盘点任务 */
export interface InventoryTask {
  id: string
  name: string
  branchId?: string
  categoryId?: string
  status: InventoryTaskStatusType
  missedRule: MissedRuleType
  repeatRule: RepeatRuleType
  createdBy: string
  startedAt?: string
  submittedAt?: string
  completedAt?: string
  rejectedAt?: string
  rejectedBy?: string
  rejectReason?: string
  createdAt: string
  updatedAt: string
}

/** 盘点项 */
export interface InventoryItem {
  id: string
  taskId: string
  assetId: string
  expectedQty: number
  actualQty?: number
  result: InventoryItemResultType
  checkCount: number
  checkedBy?: string
  checkedAt?: string
  remarks?: string
  createdAt: string
  updatedAt: string
}

/** 盘点记录 */
export interface InventoryCheck {
  id: string
  taskId: string
  itemId: string
  assetId: string
  qty: number
  checkedBy: string
  checkedAt: string
  device?: string
}

// ============ API 信封类型 ============

/** DRF 分页响应 */
export interface PaginatedResponse<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

/** DRF 错误响应 */
export type ApiError = {
  detail?: string
} & Record<string, string | string[] | undefined>

/** 登录请求 */
export interface LoginRequest {
  phone: string
  password: string
}

/** 登录响应 */
export interface LoginResponse {
  token: string
  user: User
}

// ============ 工具类型 ============

/** 分页参数 */
export interface PaginationParams {
  page?: number
  pageSize?: number
}

// ============ 报表类型 ============

/** 报表概览 */
export interface ReportOverview {
  totalAssets: number
  totalValue: number
  activeRate: number
  growthRate: number
  pendingApproval: number
  lowStockCount: number
  pendingInventory: number
}

/** 分公司统计 */
export interface BranchStat {
  name: string
  value: number
  percentage: number
}

/** 状态统计 */
export interface StatusStat {
  status: string
  count: number
  percentage: number
}

/** 分类统计 */
export interface CategoryStat {
  category: string
  count: number
  percentage: number
}

/** 盘点进度 */
export interface InventoryProgress {
  totalItems: number
  checkedItems: number
  matchedCount: number
  surplusCount: number
  missingCount: number
  uncheckedCount: number
  matchRate?: number
  surplusRate?: number
  missingRate?: number
}

/** 盘点报告 */
export interface InventoryReport {
  task: InventoryTask
  progress: InventoryProgress
  items: InventoryItem[]
}
