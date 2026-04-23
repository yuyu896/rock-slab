/* 磐盘 - 资产 API */
import request from '@/utils/request'
import type { Asset, PaginatedResponse, PaginationParams } from '@/types'

export function getAssets(params?: PaginationParams & {
  branch?: string
  category?: string
  status?: string
  keyword?: string
  ordering?: string
}) {
  return request.get<PaginatedResponse<Asset>>('/api/assets/', { params })
}

export function getAsset(id: string) {
  return request.get<Asset>(`/api/assets/${id}`)
}

export function createAsset(data: Partial<Asset>) {
  return request.post<Asset>('/api/assets/', data)
}

export function updateAsset(id: string, data: Partial<Asset>) {
  return request.put<Asset>(`/api/assets/${id}`, data)
}

export function deleteAsset(id: string) {
  return request.delete(`/api/assets/${id}`)
}

/** Excel 批量导入 */
export function importAssets(file: File) {
  const formData = new FormData()
  formData.append('file', file)
  return request.post<{ imported: number; errors: string[] }>('/api/assets/import', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

/** Excel 导出 */
export function exportAssets(params?: { branch?: string }) {
  return request.get<Blob>('/api/assets/export', { params, responseType: 'blob' })
}
