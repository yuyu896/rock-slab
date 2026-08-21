import type { User, Branch, Region, Team } from '@/types'
import { ROLE_LEVELS } from '@/constants'

export type NodeType = 'group' | 'region' | 'team' | 'branch'

export interface NodeRef {
  type: NodeType
  rawId: string
}

/**
 * 节点员工范围：沿组织树派生（员工仅挂分公司，区域/行政组归属由 branch.team 推导）。
 * 统一规则：节点员工 = 子树分公司挂靠员工 ∪ 子树内全部负责人任命
 * （branch.manager / team.leader / region.manager，即使无分公司挂靠也在其管辖节点可见）。
 * - 分公司：u.branch = 该分公司 ∪ u = branch.manager
 * - 行政组：u.branch ∈ 组内分公司 ∪ u ∈ 组内分公司负责人 ∪ u = team.leader
 * - 区域：u.branch ∈ 区域旗下分公司 ∪ u ∈ 旗下负责人 ∪ u ∈ 各组 leader ∪ u = region.manager
 * - 集团根：全部员工
 */
export function filterEmployeesByNode(
  node: NodeRef,
  data: { users: User[]; branches: Branch[]; regions: Region[]; teams: Team[] },
): User[] {
  const { users, branches, regions, teams } = data
  if (node.type === 'group') {
    return users
  }
  if (node.type === 'branch') {
    const branch = branches.find(b => b.id === node.rawId)
    return users.filter(u => u.branch === node.rawId || (branch?.manager && u.id === branch.manager))
  }
  if (node.type === 'team') {
    const teamBranches = branches.filter(b => b.team === node.rawId)
    const branchIds = new Set(teamBranches.map(b => b.id))
    const managerIds = new Set(teamBranches.filter(b => b.manager).map(b => b.manager as string))
    const team = teams.find(t => t.id === node.rawId)
    return users.filter(u =>
      (u.branch && branchIds.has(u.branch))
      || managerIds.has(u.id)
      || (team?.leader && u.id === team.leader),
    )
  }
  const regionTeams = teams.filter(t => t.region === node.rawId)
  const teamIds = new Set(regionTeams.map(t => t.id))
  const leaderIds = new Set(regionTeams.filter(t => t.leader).map(t => t.leader as string))
  const regionBranches = branches.filter(b => teamIds.has(b.team))
  const branchIds = new Set(regionBranches.map(b => b.id))
  const managerIds = new Set(regionBranches.filter(b => b.manager).map(b => b.manager as string))
  const region = regions.find(r => r.id === node.rawId)
  return users.filter(u =>
    (u.branch && branchIds.has(u.branch))
    || managerIds.has(u.id)
    || leaderIds.has(u.id)
    || (region?.manager && u.id === region.manager),
  )
}

/** 按职级排序（高职级在前），同职级按姓名。 */
export function sortEmployeesByRole(list: User[]): User[] {
  return [...list].sort((a, b) => {
    const la = ROLE_LEVELS[a.role] ?? 99
    const lb = ROLE_LEVELS[b.role] ?? 99
    if (la !== lb) return la - lb
    return (a.name || '').localeCompare(b.name || '')
  })
}
