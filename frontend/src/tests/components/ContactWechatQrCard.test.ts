import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'

const { mocks } = vi.hoisted(() => ({
  mocks: {
    isAdmin: true,
    getCompany: vi.fn(),
    uploadCompanyWechatQr: vi.fn(),
  },
}))

vi.mock('@/api/company', () => ({
  getCompany: mocks.getCompany,
  uploadCompanyWechatQr: mocks.uploadCompanyWechatQr,
}))
vi.mock('@/store/user', () => ({ useUserStore: () => ({ isAdmin: mocks.isAdmin }) }))

import ContactWechatQrCard from '@/components/ContactWechatQrCard.vue'

describe('ContactWechatQrCard', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mocks.isAdmin = true
    mocks.getCompany.mockResolvedValue({ data: { wechat_qr_code: null } })
    mocks.uploadCompanyWechatQr.mockResolvedValue({ data: { wechat_qr_code: '/media/company/contact/wechat-new.png' } })
  })

  it('显示已配置的联系二维码，普通员工没有上传入口', async () => {
    mocks.isAdmin = false
    mocks.getCompany.mockResolvedValue({ data: { wechat_qr_code: '/media/company/contact/wechat.png' } })

    const wrapper = mount(ContactWechatQrCard)
    await flushPromises()

    expect(wrapper.text()).toContain('联系微信')
    expect(wrapper.find('img').attributes('src')).toBe('/media/company/contact/wechat.png')
    expect(wrapper.find('.qr-upload-button').exists()).toBe(false)
  })

  it('管理员上传后立即显示新二维码', async () => {
    const wrapper = mount(ContactWechatQrCard)
    await flushPromises()
    const file = new File(['qr'], 'wechat.png', { type: 'image/png' })
    const input = wrapper.get('input[type="file"]')
    Object.defineProperty(input.element, 'files', { value: [file], configurable: true })

    await input.trigger('change')
    await flushPromises()

    expect(mocks.uploadCompanyWechatQr).toHaveBeenCalledWith(file)
    expect(wrapper.find('img').attributes('src')).toBe('/media/company/contact/wechat-new.png')
  })
})
