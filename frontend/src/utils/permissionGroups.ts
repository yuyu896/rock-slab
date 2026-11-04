import type { TransferActionType } from '@/types'

export type TransferPermissionSet = {
  view: string
  create: string
  createRequiresView: 'view_categories' | 'view_asset_ledger'
  edit: string
  deleteDraft: string
  submit: string
  approve: string
  withdraw: string
  import?: string
  rejectInbound?: string
}

export type ActiveTransferActionType = Exclude<TransferActionType, 'return'>

export const TRANSFER_PERMISSION_OPERATIONS: Record<ActiveTransferActionType, TransferPermissionSet> = {
  purchase: {
    view: 'view_purchase',
    create: 'edit_purchase',
    createRequiresView: 'view_categories',
    edit: 'edit_purchase',
    deleteDraft: 'delete_purchase_draft',
    submit: 'edit_purchase',
    approve: 'approve_purchase',
    withdraw: 'edit_purchase',
    import: 'edit_purchase',
  },
  assign: {
    view: 'view_assignment',
    create: 'edit_assignment',
    createRequiresView: 'view_asset_ledger',
    edit: 'edit_assignment',
    deleteDraft: 'delete_assignment_draft',
    submit: 'edit_assignment',
    approve: 'approve_assignment',
    withdraw: 'edit_assignment',
    import: 'edit_assignment',
  },
  transfer: {
    view: 'view_transfer',
    create: 'edit_transfer',
    createRequiresView: 'view_asset_ledger',
    edit: 'edit_transfer',
    deleteDraft: 'delete_transfer_draft',
    submit: 'edit_transfer',
    approve: 'approve_internal_transfer',
    withdraw: 'edit_transfer',
    import: 'edit_transfer',
    rejectInbound: 'edit_transfer',
  },
  recovery: {
    view: 'view_recovery',
    create: 'edit_recovery',
    createRequiresView: 'view_asset_ledger',
    edit: 'edit_recovery',
    deleteDraft: 'delete_recovery_draft',
    submit: 'edit_recovery',
    approve: 'approve_recovery',
    withdraw: 'edit_recovery',
  },
}

export function canManageTransfer(
  type: TransferActionType,
  can: (operation: string) => boolean,
): boolean {
  const operations = TRANSFER_PERMISSION_OPERATIONS[type as ActiveTransferActionType]
  if (!operations) return false
  return can(operations.view)
    && can(operations.edit)
    && can(operations.createRequiresView)
}

export function canCreateTransfer(
  type: TransferActionType,
  can: (operation: string) => boolean,
): boolean {
  return canManageTransfer(type, can)
}

export const TRANSFER_APPROVAL_OPERATIONS = Object.values(TRANSFER_PERMISSION_OPERATIONS)
  .map((operations) => operations.approve)

export const TRANSFER_PAGE_OPERATIONS = Object.fromEntries(
  Object.entries(TRANSFER_PERMISSION_OPERATIONS).map(([type, operations]) => [
    type,
    [...new Set(Object.values(operations).filter((code): code is string => Boolean(code)))],
  ]),
) as Record<ActiveTransferActionType, string[]>

export const APPROVAL_OPERATIONS = [...TRANSFER_APPROVAL_OPERATIONS, 'review_inventory']

export const CATEGORY_PAGE_OPERATIONS = [
  'view_categories', 'edit_categories',
]

export const ASSET_LEDGER_PAGE_OPERATIONS = [
  'view_asset_ledger', 'import_asset_ledger', 'adjust_asset_ledger',
]

export const INVENTORY_OPERATIONS = [
  'view_inventory', 'edit_inventory', 'review_inventory',
]

export const MOBILE_INVENTORY_PAGE_OPERATIONS = [
  'view_inventory', 'edit_inventory', 'review_inventory',
]

export const MY_DOCUMENT_PERMISSION_KEYS = ['create', 'view', 'edit', 'deleteDraft', 'submit', 'withdraw'] as const

export const MY_DOCUMENT_OPERATIONS = Object.values(TRANSFER_PERMISSION_OPERATIONS)
  .flatMap((operations) => MY_DOCUMENT_PERMISSION_KEYS.map((key) => operations[key]))
  .filter((code, index, all): code is string => Boolean(code) && all.indexOf(code) === index)
