/* 磐盘 - 集团（Company 单例）API */
import request from '@/utils/request'

export interface Company {
  id: string
  name: string
  wechatQrCode: string | null
}

export interface CompanyWriteOption extends Pick<Company, 'id' | 'name'> {
  canCreateRegion: boolean
}

export function getCompany(params?: { scope?: 'write' | 'tree' }) {
  return request.get<Company | CompanyWriteOption>('/api/company/', { params })
}

export function getCompanyWechatQr() {
  return request.get<Pick<Company, 'wechatQrCode'>>('/api/company/wechat-qr/')
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
