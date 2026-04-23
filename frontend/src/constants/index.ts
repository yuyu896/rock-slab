/* 磐盘 - Rock Slab 常量定义 */
import type {
  UserRoleType,
  AssetStatusType,
  ApprovalStatusType,
  InventoryTaskStatusType,
  InventoryItemResultType,
  EntityStatusType,
  MissedRuleType,
  RepeatRuleType,
} from '@/types'

// ============ 角色 ============

export const ROLE_LABELS: Record<UserRoleType, string> = {
  admin: '超级管理员',
  manager: '行政经理',
  supervisor: '行政主管',
  leader: '行政组长',
  staff: '行政专员',
}

export const ROLE_LEVELS: Record<UserRoleType, number> = {
  admin: 1,
  manager: 2,
  supervisor: 3,
  leader: 4,
  staff: 5,
}

// ============ 资产状态 ============

export const ASSET_STATUS_OPTIONS: { value: AssetStatusType; label: string }[] = [
  { value: '在库', label: '在库' },
  { value: '使用中', label: '使用中' },
  { value: '维修中', label: '维修中' },
  { value: '报废', label: '报废' },
]

export const ASSET_STATUS_COLORS: Record<AssetStatusType, { bg: string; color: string }> = {
  '在库': { bg: 'var(--color-status-in-stock-bg)', color: 'var(--color-status-in-stock-text)' },
  '使用中': { bg: 'var(--color-status-in-use-bg)', color: 'var(--color-status-in-use-text)' },
  '维修中': { bg: 'var(--color-status-repair-bg)', color: 'var(--color-status-repair-text)' },
  '报废': { bg: 'var(--color-status-scrapped-bg)', color: 'var(--color-status-scrapped-text)' },
}

// ============ 审批状态 ============

export const APPROVAL_STATUS_OPTIONS: { value: ApprovalStatusType; label: string }[] = [
  { value: '待审批', label: '待审批' },
  { value: '已通过', label: '已通过' },
  { value: '已驳回', label: '已驳回' },
  { value: '已入库', label: '已入库' },
]

export const APPROVAL_STATUS_COLORS: Record<ApprovalStatusType, { bg: string; color: string }> = {
  '待审批': { bg: 'var(--color-approval-pending-bg)', color: 'var(--color-approval-pending-text)' },
  '已通过': { bg: 'var(--color-approval-approved-bg)', color: 'var(--color-approval-approved-text)' },
  '已驳回': { bg: 'var(--color-approval-rejected-bg)', color: 'var(--color-approval-rejected-text)' },
  '已入库': { bg: 'var(--color-status-in-stock-bg)', color: 'var(--color-status-in-stock-text)' },
}

// ============ 盘点任务状态 ============

export const INVENTORY_STATUS_MAP: Record<InventoryTaskStatusType, string> = {
  pending: '待盘点',
  in_progress: '盘点中',
  pending_review: '待审核',
  completed: '已完成',
  rejected: '已驳回',
  cancelled: '已作废',
}

export const INVENTORY_STATUS_OPTIONS: { value: InventoryTaskStatusType; label: string }[] = [
  { value: 'pending', label: '待盘点' },
  { value: 'in_progress', label: '盘点中' },
  { value: 'pending_review', label: '待审核' },
  { value: 'completed', label: '已完成' },
  { value: 'rejected', label: '已驳回' },
  { value: 'cancelled', label: '已作废' },
]

export const INVENTORY_STATUS_COLORS: Record<InventoryTaskStatusType, { bg: string; color: string }> = {
  pending: { bg: 'var(--color-approval-pending-bg)', color: 'var(--color-approval-pending-text)' },
  in_progress: { bg: 'var(--color-status-in-use-bg)', color: 'var(--color-status-in-use-text)' },
  pending_review: { bg: 'var(--color-approval-pending-bg)', color: 'var(--color-approval-pending-text)' },
  completed: { bg: 'var(--color-status-in-stock-bg)', color: 'var(--color-status-in-stock-text)' },
  rejected: { bg: 'var(--color-approval-rejected-bg)', color: 'var(--color-approval-rejected-text)' },
  cancelled: { bg: 'var(--color-inventory-unchecked-bg)', color: 'var(--color-inventory-unchecked-text)' },
}

// ============ 盘点结果 ============

export const INVENTORY_RESULT_MAP: Record<InventoryItemResultType, string> = {
  matched: '正常',
  surplus: '盘盈',
  missing: '盘亏',
  unchecked: '未盘点',
}

export const INVENTORY_RESULT_COLORS: Record<InventoryItemResultType, { bg: string; color: string }> = {
  matched: { bg: 'var(--color-primary-100)', color: 'var(--color-primary-700)' },
  surplus: { bg: 'var(--color-inventory-surplus-bg)', color: 'var(--color-inventory-surplus-text)' },
  missing: { bg: 'var(--color-inventory-missing-bg)', color: 'var(--color-inventory-missing-text)' },
  unchecked: { bg: 'var(--color-inventory-unchecked-bg)', color: 'var(--color-inventory-unchecked-text)' },
}

// ============ 实体状态 ============

export const ENTITY_STATUS_LABELS: Record<EntityStatusType, string> = {
  active: '正常',
  inactive: '已停用',
}

export const ENTITY_STATUS_COLORS: Record<EntityStatusType, { bg: string; color: string }> = {
  active: { bg: 'var(--color-primary-100)', color: 'var(--color-primary-700)' },
  inactive: { bg: 'var(--color-inventory-unchecked-bg)', color: 'var(--color-inventory-unchecked-text)' },
}

// ============ 资产类目编码 ============

export const ASSET_CATEGORY_CODES: Record<string, string> = {
  '固定资产类': 'A',
  '低值易耗品': 'B',
  '无形资产类': 'C',
  '文档资料类': 'D',
  '特殊设备类': 'E',
  '其他资产': 'F',
}

export const ITEM_CATEGORY_CODES: Record<string, string> = {
  '办公设备': 'a',
  '电子设备': 'b',
  '清洁用品': 'c',
  '软件与数据': 'd',
  '行政文件': 'e',
  '安防设备': 'f',
  '其他': 'g',
}

// ============ 盘点规则 ============

export const MISSED_RULE_LABELS: Record<MissedRuleType, string> = {
  keep: '保持不变',
  zero: '清零处理',
}

export const REPEAT_RULE_LABELS: Record<RepeatRuleType, string> = {
  last: '以最后一次为准',
  accumulate: '累计数量',
}

// ============ 分公司编号格式 ============

export const BRANCH_CODE_PATTERN = '^[A-Z]{2,4}[0-9]{3}$'
export const BRANCH_CODE_HINT = '2-4位大写字母(城市缩写)+3位数字，如 SH001'
