/* 磐盘 - 集团（Company 单例）API */
import request from '@/utils/request'

export interface Company {
  id: string
  name: string
  wechat_qr_code: string | null
}

export function getCompany() {
  return request.get<Company>('/api/company/')
}

export function updateCompany(data: Partial<Pick<Company, 'name'>>) {
  return request.patch<Company>('/api/company/', data)
}

export function uploadCompanyWechatQr(file: File) {
  const formData = new FormData()
  formData.append('wechat_qr_code', file)
  return request.post<Company>('/api/company/wechat-qr/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}
