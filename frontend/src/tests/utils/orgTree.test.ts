import { describe, it, expect } from 'vitest'
import { filterEmployeesByNode, sortEmployeesByRole } from '@/utils/orgTree'
import type { User, Branch, Region, Team } from '@/types'

function makeUser(p: Partial<User> & { id: string }): User {
  return { phone: '13800000000', name: p.id, role: 'staff', status: 'active', ...p } as User
}
function makeBranch(p: Partial<Branch> & { id: string; region: string; team: string }): Branch {
  return { name: p.id, code: p.id.toUpperCase(), address: '', status: 'active', ...p } as Branch
}
function makeRegion(p: Partial<Region> & { id: string }): Region {
  return { name: p.id, code: p.id.toUpperCase(), status: 'active', createdAt: '', updatedAt: '', ...p } as Region
}
function makeTeam(p: Partial<Team> & { id: string; region: string }): Team {
  return { name: p.id, status: 'active', createdAt: '', updatedAt: '', ...p } as Team
}

// 树：r1 → [t1 → b1,b2 | t2 → b3]；r2 → t3 → b4
const regions: Region[] = [makeRegion({ id: 'r1' }), makeRegion({ id: 'r2', manager: 'chief' })]
const teams: Team[] = [
  makeTeam({ id: 't1', region: 'r1', leader: 'zhang' }),
  makeTeam({ id: 't2', region: 'r1' }),
  makeTeam({ id: 't3', region: 'r2' }),
]
const branches: Branch[] = [
  makeBranch({ id: 'b1', region: 'r1', team: 't1', manager: 'boss' }),
  makeBranch({ id: 'b2', region: 'r1', team: 't1' }),
  makeBranch({ id: 'b3', region: 'r1', team: 't2' }),
  makeBranch({ id: 'b4', region: 'r2', team: 't3' }),
]
const users: User[] = [
  makeUser({ id: 'u1', branch: 'b1' }),
  makeUser({ id: 'u2', branch: 'b2' }),
  makeUser({ id: 'u3', branch: 'b3' }),
  makeUser({ id: 'u4', branch: 'b4' }),
  makeUser({ id: 'zhang' }), // 组长：无分公司挂靠，t1.leader
  makeUser({ id: 'chief' }), // 区长：无分公司挂靠，r2.manager
  makeUser({ id: 'boss' }),  // 分公司负责人：b1.manager
  makeUser({ id: 'orphan' }),// 无任何归属
]
const data = { users, branches, regions, teams }
const ids = (us: User[]) => us.map(u => u.id).sort()

describe('filterEmployeesByNode（沿树派生 + 负责人并入）', () => {
  it('分公司节点：该分公司员工 ∪ 分公司负责人', () => {
    expect(ids(filterEmployeesByNode({ type: 'branch', rawId: 'b1' }, data))).toEqual(['boss', 'u1'])
  })

  it('行政组节点：组内分公司员工 ∪ 组长（无分公司挂靠也可见）', () => {
    expect(ids(filterEmployeesByNode({ type: 'team', rawId: 't1' }, data))).toEqual(['boss', 'u1', 'u2', 'zhang'])
  })

  it('区域节点：旗下（经行政组）分公司员工 ∪ 区长 ∪ 各组组长', () => {
    expect(ids(filterEmployeesByNode({ type: 'region', rawId: 'r1' }, data))).toEqual([
      'boss', 'u1', 'u2', 'u3', 'zhang',
    ])
    expect(ids(filterEmployeesByNode({ type: 'region', rawId: 'r2' }, data))).toEqual([
      'chief', 'u4',
    ])
  })

  it('跨区域隔离：r2 不含 r1 员工', () => {
    expect(filterEmployeesByNode({ type: 'region', rawId: 'r2' }, data).some(u => u.id.startsWith('u1'))).toBe(false)
  })

  it('集团根：返回所有员工（含无归属员工）', () => {
    const all = filterEmployeesByNode({ type: 'group', rawId: '' }, data)
    expect(ids(all)).toEqual(ids(users))
  })

  it('无分公司挂靠且不任负责人的员工仅在集团根可见', () => {
    expect(filterEmployeesByNode({ type: 'region', rawId: 'r1' }, data).some(u => u.id === 'orphan')).toBe(false)
    expect(filterEmployeesByNode({ type: 'group', rawId: '' }, data).some(u => u.id === 'orphan')).toBe(true)
  })
})

describe('sortEmployeesByRole', () => {
  it('高职级在前，同职级按姓名', () => {
    const sorted = sortEmployeesByRole([
      makeUser({ id: 'b', role: 'staff' }),
      makeUser({ id: 'a', role: 'manager' }),
      makeUser({ id: 'c', role: 'leader' }),
    ])
    expect(sorted.map(u => u.id)).toEqual(['a', 'c', 'b'])
  })
})
