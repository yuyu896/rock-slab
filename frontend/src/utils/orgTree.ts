import type { User, Branch } from '@/types'

export type NodeType = 'region' | 'team' | 'branch'

export interface NodeRef {
  type: NodeType
  rawId: string
  regionId?: string
}

/**
 * 节点员工范围：员工按最具体归属呈现。
 * - 分公司：u.branch = 该分公司
 * - 真实行政组：该组分公司员工 ∪ 直属该组的无分公司员工（branch 为空且 team=该组）
 * - 未分组节点（rawId 空）：该区域 team=null 分公司的员工
 * - 区域：u.region = 该区域（含无分公司员工）
 */
export function filterEmployeesByNode(
  node: NodeRef,
  data: { users: User[]; branches: Branch[] },
): User[] {
  const { users, branches } = data
  if (node.type === 'branch') {
    return users.filter(u => u.branch === node.rawId)
  }
  if (node.type === 'team') {
    if (node.rawId) {
      const branchIds = branches.filter(b => b.team === node.rawId).map(b => b.id)
      return users.filter(u => (u.branch && branchIds.includes(u.branch)) || (!u.branch && u.team === node.rawId))
    }
    const branchIds = branches.filter(b => b.region === node.regionId && !b.team).map(b => b.id)
    return users.filter(u => u.branch && branchIds.includes(u.branch))
  }
  return users.filter(u => u.region === node.rawId)
}
