/* 磐盘 - Rock Slab 类型定义 */

// ============ 枚举 ============

/** 用户角色 */
export const UserRole = {
  ADMIN: 'admin',
  DIRECTOR: 'director',
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
  DRAFT: '草稿',
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

/** 分公司（region 为派生只读字段 = team.region） */
export interface Branch {
  id: string
  name: string
  code: string
  region: string
  team: string
  address: string
  manager?: string
  phone?: string
  status: EntityStatusType
  createdAt: string
  updatedAt: string
}

/** 品目字典（P1：计数字段下线，数量事实唯一存放于台账） */
export interface Category {
  id?: string
  资产类目: string
  物品分类: string
  资产名称: string
  资产编号: string
  规格?: string
  管理方式?: 'quantity' | 'instance'
  是否租用?: boolean
  默认供应商?: string
  计量单位: string
  警戒线?: number | null
  备注?: string
  createdAt?: string
  updatedAt?: string
}

/** 创建/更新分类的请求体（使用英文字段名） */
export interface CategoryRequest {
  asset_category: string
  item_category: string
  asset_name: string
  asset_code: string
  specification?: string
  management_type?: 'quantity' | 'instance'
  is_rental?: boolean
  default_supplier?: string
  unit: string
  warning_line?: number | null
  remarks?: string
}


/** 台账行（P1：一行 = 分公司 × 品目，数量四列，品目信息联字典） */
export interface AssetStock {
  id: string
  branch: string
  branchName?: string
  item: string
  资产编号: string
  资产名称?: string
  规格?: string
  资产类目?: string
  物品分类?: string
  计量单位?: string
  管理方式?: 'quantity' | 'instance'
  在库数量: number
  在用数量: number
  回收库数量: number
  总量?: number
  警戒线?: number | null
  生效警戒线?: number | null
  是否充足?: boolean
  createdAt?: string
  updatedAt?: string
}

/** 台账增量导入差异行 */
export interface LedgerImportDiff {
  行号: number
  分公司: string
  资产编号: string
  资产名称?: string
  现值: number
  导入值: number
  变动量: number
}

/** 台账调整单（P3：编号 + 来源盘点任务；创建即生效） */
export interface LedgerAdjustment {
  id: string
  单据编号: string
  branch: string
  branchName?: string
  item: string
  资产编号: string
  资产名称?: string
  目标列: string
  变动量: number
  事由: string
  经办人?: string | null
  经办人姓名?: string | null
  isInitial?: boolean
  sourceTask?: string | null
  来源任务?: string | null
  createdAt?: string
}

/** 用户 */
export interface User {
  id: string
  phone: string
  name: string
  branch?: string
  branchName?: string
  regionName?: string
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

/** 调拨/流转记录：单头 + 明细行（P2 明细行化） */
export type TransferActionType = 'purchase' | 'assign' | 'return' | 'transfer' | 'recovery'

/** 品目字典摘要（ItemPicker 点选结果） */
export interface ItemSummary {
  id: string
  asset_code: string
  asset_name: string
  specification?: string
  unit?: string
  assetCategory?: string
  itemCategory?: string
  managementType?: string
}

/** 流转单明细行（品目信息由后端联字典回显） */
export interface TransferLine {
  id: string
  行号: number
  item: string
  itemCode: string
  itemName: string
  itemSpec?: string
  unit?: string
  assetCategory?: string
  itemCategory?: string
  managementType?: 'quantity' | 'instance'
  数量: number
  本批规格?: string
  单价?: number | null
  金额?: number | null
  使用人?: string
  department?: string | null
  departmentName?: string
  存放位置?: string
  /** 行关联实例（实例管理品目）：内部编号列表，可跳转实例生平 */
  instances?: { id: string; code: string }[]
}

/** 明细行创建入参（品目为字典 uuid；实例引用为实例 uuid 数组） */
export interface TransferLineInput {
  item: string
  数量: number
  本批规格?: string
  单价?: number | null
  金额?: number | null
  使用人?: string
  department?: string | null
  存放位置?: string
  instances?: string[]
}

export interface TransferDocument {
  id: string
  单据编号: string
  调拨日期: string
  调出分公司?: string
  调出部门?: string
  调入分公司?: string
  调入部门?: string
  from_branch?: string
  to_branch?: string
  fromBranchName?: string
  toBranchName?: string
  调拨原因?: string
  供应商?: string
  需求部门?: string
  调出负责人?: string
  调入负责人?: string
  用途?: string
  回收分类?: string
  回收去向?: 'recycle_bin' | 'dispose'
  领用来源?: 'stock' | 'recycle_bin'
  处置方式?: '出售' | '报废' | '捐赠' | ''
  处置金额?: number
  出库日期?: string
  采购经办人?: string
  备注?: string
  审批状态: ApprovalStatusType
  审批人?: string
  审批时间?: string
  创建人: string
  action_type?: TransferActionType
  lines: TransferLine[]
  品项数?: number
  总数量?: number
  createdAt: string
  updatedAt: string
}

/** 兼容别名：既有代码沿用 Transfer 名 */
export type Transfer = TransferDocument

/** 单据摘要：多行单据的首行品目 + 等N项（通知/列表/移动端展示用） */
export function transferDocSummary(doc: TransferDocument): {
  name: string
  code: string
  qty: number
} {
  const lines = doc.lines ?? []
  if (lines.length === 0) return { name: doc.单据编号 || '-', code: '-', qty: 0 }
  const first = lines[0]
  return {
    name: first.itemName + (lines.length > 1 ? ` 等 ${lines.length} 项` : ''),
    code: first.itemCode,
    qty: lines.reduce((sum, line) => sum + (line.数量 || 0), 0),
  }
}

/** 盘点任务 */
export interface InventoryTask {
  id: string
  name: string
  branchId?: string
  branch?: string
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
  stockId: string
  assetCode?: string
  assetName?: string
  branchName?: string
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

/** 固定资产实例档案（P2 第二刀：品目联字典、供应商/单价/采购日期经出生行派生） */
export interface FixedAsset {
  id: string
  内部编号: string
  序列号: string
  /** 序列号为空 = 待补录 */
  待补录?: boolean
  当前状态: '在库' | '在用' | '回收库' | '退役'
  使用人?: string
  department?: string | null
  departmentName?: string
  branch?: string | null
  branchName?: string
  item: string
  itemCode: string
  itemName: string
  itemSpec?: string
  assetCategory?: string
  itemCategory?: string
  managementType?: 'quantity' | 'instance'
  入库日期?: string | null
  供应商?: string
  单价?: number | string | null
  采购日期?: string | null
  备注?: string
  createdAt: string
  updatedAt: string
}

/** 实例生平（出生信息 + 关联全部明细行倒序） */
export interface FixedAssetTimeline {
  instance: FixedAsset
  birth: {
    transferId: string
    单据编号: string
    日期: string
    供应商: string
    单价: number | null
    采购日期: string
  } | null
  timeline: {
    transferId: string
    单据编号: string
    actionType: string
    日期: string
    行号: number
    品目编号: string
    数量: number
    使用人: string
    部门: string
    本批规格: string
    审批状态: string
  }[]
}

/** 盘点记录 */
export interface InventoryCheck {
  id: string
  taskId: string
  itemId: string
  stockId: string
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
