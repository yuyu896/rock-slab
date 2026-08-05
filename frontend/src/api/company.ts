/* 磐盘 - 集团（Company 单例）API */
import request from '@/utils/request'

export interface Company {
  id: string
  name: string
}

export function getCompany() {
  return request.get<Company>('/api/company/')
}

export function updateCompany(data: Partial<Pick<Company, 'name'>>) {
  return request.patch<Company>('/api/company/', data)
}
