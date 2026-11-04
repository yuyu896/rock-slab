import { describe, expect, it } from 'vitest'
import { TRANSFER_TYPES } from '@/constants'
import { TRANSFER_PERMISSION_OPERATIONS } from '@/utils/permissionGroups'

describe('归还历史类型', () => {
  it('保留历史类型标签，但不作为编辑器支持类型', () => {
    expect(TRANSFER_TYPES.return.label).toBe('归还入库')
    expect(Object.keys(TRANSFER_TYPES)).toContain('return')
    expect(TRANSFER_PERMISSION_OPERATIONS).not.toHaveProperty('return')
  })
})
