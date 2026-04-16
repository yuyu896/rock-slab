/* 磐盘 - 行政组 API */
import request from '@/utils/request'
import type { Team, PaginationParams } from '@/types'

export function getTeams(params?: PaginationParams & { region?: string }) {
  return request.get<Team[]>('/api/teams/', { params })
}

export function getTeam(id: string) {
  return request.get<Team>(`/api/teams/${id}`)
}

export function createTeam(data: Partial<Team>) {
  return request.post<Team>('/api/teams/', data)
}

export function updateTeam(id: string, data: Partial<Team>) {
  return request.put<Team>(`/api/teams/${id}`, data)
}

export function deleteTeam(id: string) {
  return request.delete(`/api/teams/${id}`)
}
