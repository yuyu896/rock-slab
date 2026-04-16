/* 磐盘 - 资产类目 API */
import request, { TOKEN_KEY } from '@/utils/request'
import type { Category, CategoryRequest } from '@/types'

export function getCategories(params?: { 资产类目?: string; 物品分类?: string; keyword?: string; page?: number; pageSize?: number }) {
  return request.get<{ count: number; results: Category[] }>('/api/categories/', { params })
}

export function getCategory(id: string) {
  return request.get<Category>(`/api/categories/${id}`)
}

export function createCategory(data: CategoryRequest) {
  return request.post<Category>('/api/categories/', data)
}

export function updateCategory(id: string, data: Partial<CategoryRequest>) {
  return request.put<Category>(`/api/categories/${id}`, data)
}

export function deleteCategory(id: string) {
  return request.delete(`/api/categories/${id}`)
}

/** Excel 批量导入分类 */
export function importCategories(file: File) {
  const formData = new FormData()
  formData.append('file', file)
  return request.post<{ imported: number; errors: string[] }>('/api/categories/import', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

/** 下载分类导入模板 */
export function downloadCategoryTemplate() {
  return request.get<Blob>('/api/categories/template', { responseType: 'blob' })
}

/** 导出分类数据为 Excel */
export function exportCategories(params?: { 资产类目?: string; keyword?: string }) {
  const query = new URLSearchParams()
  if (params?.资产类目) query.set('资产类目', params.资产类目)
  if (params?.keyword) query.set('keyword', params.keyword)
  const url = `/api/categories/export${query.toString() ? '?' + query.toString() : ''}`
  const token = localStorage.getItem(TOKEN_KEY) || ''
  fetch(url, { headers: { Authorization: `Token ${token}` } })
    .then(res => res.blob())
    .then(blob => {
      const blobUrl = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = blobUrl
      link.download = '分类数据导出.xlsx'
      link.click()
      URL.revokeObjectURL(blobUrl)
    })
}
