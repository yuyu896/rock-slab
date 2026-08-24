import type { ItemSummary } from '@/types'
import type { TransferLine, TransferLineInput } from '@/types'

/** 明细行草稿：品目对象 + 数量 + 类型专属记录性字段 + 实例引用（实例管理品目） */
export interface LineDraft {
  key: number
  item: ItemSummary | null
  数量: number
  本批规格: string
  单价: number | null
  金额: number | null
  使用人: string
  department: string | null
  存放位置: string
  /** 选中的实例（id 提交、code 回显）；实例管理品目的绑定类单据必填 */
  instances: { id: string; code: string }[]
}

let seq = 0
export function emptyDraft(): LineDraft {
  seq += 1
  return {
    key: seq,
    item: null,
    数量: 1,
    本批规格: '',
    单价: null,
    金额: null,
    使用人: '',
    department: null,
    存放位置: '',
    instances: [],
  }
}

/** 草稿行 → 提交 items（未选品目的行被忽略） */
export function draftsToItems(drafts: LineDraft[]): TransferLineInput[] {
  return drafts
    .filter((d) => d.item)
    .map((d) => ({
      item: d.item!.id,
      数量: d.数量,
      本批规格: d.本批规格 || undefined,
      单价: d.单价 ?? undefined,
      金额: d.金额 ?? undefined,
      使用人: d.使用人 || undefined,
      department: d.department ?? undefined,
      存放位置: d.存放位置 || undefined,
      instances: d.instances.length ? d.instances.map((i) => i.id) : undefined,
    }))
}

/** 既有明细行 → 编辑草稿（驳回后编辑预填） */
export function draftsFromLines(lines: TransferLine[]): LineDraft[] {
  if (lines.length === 0) return [emptyDraft()]
  return lines.map((line) => {
    const draft = emptyDraft()
    draft.item = {
      id: line.item,
      asset_code: line.itemCode,
      asset_name: line.itemName,
      specification: line.itemSpec,
      unit: line.unit,
      assetCategory: line.assetCategory,
      itemCategory: line.itemCategory,
      managementType: line.managementType,
    }
    draft.数量 = line.数量
    draft.本批规格 = line.本批规格 || ''
    draft.单价 = line.单价 ?? null
    draft.金额 = line.金额 ?? null
    draft.使用人 = line.使用人 || ''
    draft.department = line.department ?? null
    draft.存放位置 = line.存放位置 || ''
    draft.instances = (line.instances || []).map((i) => ({ id: i.id, code: i.code }))
    return draft
  })
}
