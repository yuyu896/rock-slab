import { describe, it, expect } from 'vitest'
import { filterEmployeesByNode, sortEmployeesByRole } from '@/utils/orgTree'
import type { User, Branch } from '@/types'

function makeUser(p: Partial<User> & { id: string }): User {
  return { phone: '13800000000', name: p.id, role: 'staff', status: 'active', ...p } as User
}
function makeBranch(p: Partial<Branch> & { id: string; region: string }): Branch {
  return { name: p.id, code: p.id.toUpperCase(), address: '', status: 'active', ...p } as Branch
}

const branches: Branch[] = [
  makeBranch({ id: 'b1', region: 'r1', team: 't1' }),
  makeBranch({ id: 'b2', region: 'r1', team: 't1' }),
  makeBranch({ id: 'b3', region: 'r1' }), // team=null：未分组分公司
  makeBranch({ id: 'b4', region: 'r2', team: 't2' }),
]
const users: User[] = [
  makeUser({ id: 'u1', branch: 'b1', team: 't1', region: 'r1' }),
  makeUser({ id: 'u2', branch: 'b2', team: 't1', region: 'r1' }),
  makeUser({ id: 'u3', branch: 'b3', region: 'r1' }), // 未分组分公司员工
  makeUser({ id: 'zhang', branch: undefined, team: 't1', region: 'r1' }), // 张三：无分公司，直属A组
  makeUser({ id: 'sun', branch: undefined, team: undefined, region: 'r1' }), // 孙七：区域直属
  makeUser({ id: 'u4', branch: 'b4', team: 't2', region: 'r2' }),
]
const data = { users, branches }
const ids = (us: User[]) => us.map(u => u.id).sort()

describe('filterEmployeesByNode', () => {
  it('分公司节点：只返回该分公司员工', () => {
    expect(ids(filterEmployeesByNode({ type: 'branch', rawId: 'b1' }, data))).toEqual(['u1'])
  })

  it('真实行政组节点：含该组分公司员工 + 直属该组的无分公司员工（张三）', () => {
    expect(ids(filterEmployeesByNode({ type: 'team', rawId: 't1' }, data))).toEqual(['u1', 'u2', 'zhang'])
  })

  it('未分组节点：返回该区域 team=null 分公司的员工（修 bug，不再返回空）', () => {
    expect(ids(filterEmployeesByNode({ type: 'team', rawId: '', regionId: 'r1' }, data))).toEqual(['u3'])
  })

  it('区域节点：返回该区域全员（含无分公司、无行政组员工）', () => {
    expect(ids(filterEmployeesByNode({ type: 'region', rawId: 'r1' }, data))).toEqual([
      'sun', 'u1', 'u2', 'u3', 'zhang',
    ])
  })

  it('nodeCount 依据：未分组节点人数正确', () => {
    expect(filterEmployeesByNode({ type: 'team', rawId: '', regionId: 'r1' }, data).length).toBe(1)
  })

  it('跨区域隔离：r2 区域不含 r1 员工', () => {
    expect(ids(filterEmployeesByNode({ type: 'region', rawId: 'r2' }, data))).toEqual(['u4'])
  })

  it('集团根：返回所有员工（一览全员）', () => {
    const all = filterEmployeesByNode({ type: 'group', rawId: '' }, data)
    expect(all.length).toBe(users.length)
    expect(ids(all).length).toBe(6)
  })

  it('sortEmployeesByRole：按职级排序，高职级在前，同职级按姓名', () => {
    const mixed: User[] = [
      makeUser({ id: 's1', role: 'staff', name: 'B' }),
      makeUser({ id: 'a1', role: 'admin', name: 'C' }),
      makeUser({ id: 'm1', role: 'manager', name: 'D' }),
      makeUser({ id: 's2', role: 'staff', name: 'A' }),
    ]
    expect(sortEmployeesByRole(mixed).map(u => u.id)).toEqual(['a1', 'm1', 's2', 's1'])
  })
})
