const ASSET_HEADERS = [
  '序号', '分公司', '资产编号', '分公司编号', '资产类目',
  '电脑序列号', '供应商', '物品分类', '资产名称', '图片',
  '入库日期', '是否租用', '数量', '规格', '单价',
  '购入金额', '出库日期', '所属部门', '使用人', '当前状态',
  '警戒线', '是否充足', '备注',
]

const PURCHASE_HEADERS = [
  '采购日期', '分公司', '资产编号', '物品名称', '规格型号', '图片',
  '供应商', '采购数量', '单价', '总金额', '需求部门', '采购经办人', '备注',
]

const ASSIGN_HEADERS = [
  '分公司', '日期', '领用物品', '领用数量', '用途', '领用部门', '备注',
]

const TRANSFER_HEADERS = [
  '调拨日期', '调出分公司', '调出部门', '调入分公司', '调入部门',
  '资产编号', '资产名称', '规格型号', '调拨数量', '调拨原因',
  '调出负责人', '调入负责人', '备注',
]

const CATEGORY_HEADERS = [
  '资产类目', '物品分类', '资产名称', '资产编号', '计量单位', '警戒线', '备注',
]

async function buildTemplate(headers: string[], sheetName: string, filename: string) {
  const XLSX = await import('xlsx')
  const wb = XLSX.utils.book_new()
  const ws = XLSX.utils.aoa_to_sheet([headers])
  XLSX.utils.book_append_sheet(wb, ws, sheetName)
  XLSX.writeFile(wb, `${filename}.xlsx`)
}

export function generateAssetTemplate() {
  return buildTemplate(ASSET_HEADERS, '资产列表', '资产导入模板')
}

export function generateTransferTemplate(filename: string, type: string) {
  const headersMap: Record<string, string[]> = {
    purchase: PURCHASE_HEADERS,
    assign: ASSIGN_HEADERS,
    transfer: TRANSFER_HEADERS,
  }
  const sheetMap: Record<string, string> = {
    purchase: '采购入库',
    assign: '领用出库',
    transfer: '调拨',
  }
  return buildTemplate(headersMap[type] || TRANSFER_HEADERS, sheetMap[type] || '流转记录', filename)
}

export function generateCategoryTemplate() {
  return buildTemplate(CATEGORY_HEADERS, '资产分类', '分类导入模板')
}
