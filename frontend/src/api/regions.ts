/* 磐盘 - 区域 API */
import request from '@/utils/request'
import type { Region } from '@/types'

export function getRegions() {
  return request.get<Region[]>('/api/regions/')
}

export function getRegion(id: string) {
  return request.get<Region>(`/api/regions/${id}`)
}

export function createRegion(data: Partial<Region>) {
  return request.post<Region>('/api/regions/', data)
}

export function updateRegion(id: string, data: Partial<Region>) {
  return request.put<Region>(`/api/regions/${id}`, data)
}

export function deleteRegion(id: string) {
  return request.delete(`/api/regions/${id}`)
}
