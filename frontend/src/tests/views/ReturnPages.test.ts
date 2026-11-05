import { describe, expect, it } from 'vitest'
import { TRANSFER_TYPES } from '@/constants'
import { transferDocSummary } from '@/types'

describe('归还历史数据兼容', () => {
  it('保留归还类型的历史展示标签', () => {
    expect(TRANSFER_TYPES.return.label).toBe('归还入库')
  })

  it('历史归还单仍可生成通用单据摘要', () => {
    expect(transferDocSummary({
      id: 'return-1',
      单据编号: 'GH20261022-001',
      调拨日期: '2026-10-22',
      审批状态: '已通过',
      创建人: '张三',
      actionType: 'return',
      lines: [{
        id: 'line-1',
        行号: 1,
        item: 'item-1',
        itemCode: 'NB-001',
        itemName: '笔记本',
        数量: 1,
      }],
      createdAt: '',
      updatedAt: '',
    }).name).toBe('笔记本')
  })
})
