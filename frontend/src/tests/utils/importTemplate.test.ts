import { describe, it, expect, vi, beforeEach } from 'vitest'

const worksheetLog: { title: string; rows: string[][] }[] = []

vi.mock('exceljs', () => {
  const makeWs = (title: string) => {
    const entry = { title, rows: [] as string[][] }
    worksheetLog.push(entry)
    return {
      addRow: (row: string[]) => { entry.rows.push(row); return { eachCell: () => {}, height: 0 } },
      getColumn: () => ({ width: 0 }),
      views: [],
    }
  }
  const WorkbookMock = class {
    worksheets: Record<string, unknown>[] = []
    addWorksheet(title: string) {
      const ws = makeWs(title)
      this.worksheets.push(ws)
      return ws
    }
    xlsx = { writeBuffer: async () => new ArrayBuffer(8) }
  }
  // 命名空间顶层与 default 都暴露（兼容动态 import 的两种解构）
  return { Workbook: WorkbookMock, default: { Workbook: WorkbookMock } }
})

const clickSpy = vi.fn()
const createObjectURLSpy = vi.fn(() => 'blob:mock')
const revokeObjectURLSpy = vi.fn()

beforeEach(() => {
  worksheetLog.length = 0
  clickSpy.mockClear()
  createObjectURLSpy.mockClear()
  revokeObjectURLSpy.mockClear()
  vi.stubGlobal('URL', { ...URL, createObjectURL: createObjectURLSpy, revokeObjectURL: revokeObjectURLSpy })
  vi.spyOn(document, 'createElement').mockImplementation(((tag: string) => {
    const el = { tag, click: clickSpy, set download(v: string) { (this as any)._d = v }, get download() { return (this as any)._d }, href: '' } as unknown as HTMLElement
    return el
  }) as any)
})

describe('generateCategoryTemplate（sheet 名定管理方式）', () => {
  it('生成三张工作表，表名为三档管理方式', async () => {
    const { generateCategoryTemplate } = await import('@/utils/importTemplate')
    await generateCategoryTemplate()

    const titles = worksheetLog.map(ws => ws.title)
    expect(titles).toEqual(['数量管理', '实例管理', '消耗品'])

    const HEADERS = ['资产类目', '物品分类', '资产名称', '资产编号', '计量单位', '警戒线', '备注']
    for (const ws of worksheetLog) {
      expect(ws.rows[0]).toEqual(HEADERS)
    }

    expect(clickSpy).toHaveBeenCalled()
    expect(revokeObjectURLSpy).toHaveBeenCalled()
  })
})
