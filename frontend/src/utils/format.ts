/* 磐盘 - Rock Slab 格式化工具 */
import { ROLE_LABELS, INVENTORY_STATUS_MAP, INVENTORY_RESULT_MAP, ENTITY_STATUS_LABELS } from '@/constants'
import type { UserRoleType, InventoryTaskStatusType, InventoryItemResultType, EntityStatusType } from '@/types'

/** 货币格式化 */
export function formatMoney(value: number): string {
  if (value >= 10000) {
    return `¥${(value / 10000).toFixed(1)}万`
  }
  return `¥${value.toLocaleString('zh-CN', { minimumFractionDigits: 0, maximumFractionDigits: 2 })}`
}

/** 日期格式化 (YYYY-MM-DD) */
export function formatDate(date: string | Date): string {
  const d = typeof date === 'string' ? new Date(date) : date
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

/** 日期时间格式化 (YYYY-MM-DD HH:mm) */
export function formatDateTime(date: string | Date): string {
  const d = typeof date === 'string' ? new Date(date) : date
  const dateStr = formatDate(d)
  const h = String(d.getHours()).padStart(2, '0')
  const min = String(d.getMinutes()).padStart(2, '0')
  return `${dateStr} ${h}:${min}`
}

/** 百分比格式化 */
export function formatPercentage(value: number, decimals = 1): string {
  return `${value.toFixed(decimals)}%`
}

/** 角色名称映射 */
export function getRoleName(role: UserRoleType): string {
  return ROLE_LABELS[role] || role
}

/** 盘点任务状态标签 */
export function getInventoryStatusLabel(status: InventoryTaskStatusType): string {
  return INVENTORY_STATUS_MAP[status] || status
}

/** 盘点结果标签 */
export function getInventoryResultLabel(result: InventoryItemResultType): string {
  return INVENTORY_RESULT_MAP[result] || result
}

/** 实体状态标签 */
export function getEntityStatusLabel(status: EntityStatusType): string {
  return ENTITY_STATUS_LABELS[status] || status
}
