/* 磐盘 - 资产类目 API */
import request from '@/utils/request'
import type { Category, CategoryRequest } from '@/types'

export function getCategories(params?: { 资产类目?: string; 物品分类?: string; keyword?: string; page?: number; pageSize?: number }) {
  return request.get<{ count: number; results: Category[] }>('/api/categories/', { params })
}

export function getCategory(id: string) {
  return request.get<Category>(`/api/categories/${id}`)
}

/** 按资产编号精确查询分类（新增表单失焦反查名称/类目/分类） */
export function lookupCategoryByCode(assetCode: string) {
  return request.get<{ id: string; 资产名称: string; 资产类目: string; 物品分类: string; 计量单位: string; 警戒线: number | null }>(
    '/api/categories/lookup',
    { params: { asset_code: assetCode } },
  )
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

/** 导出分类数据为 Excel（走统一请求实例，401/400 由拦截器处理） */
export async function exportCategories(params?: { 资产类目?: string; keyword?: string }) {
  const { data: blob } = await request.get<Blob>('/api/categories/export', {
    params,
    responseType: 'blob',
  })
  const blobUrl = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = blobUrl
  link.download = '分类数据导出.xlsx'
  link.click()
  URL.revokeObjectURL(blobUrl)
}
