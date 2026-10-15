import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'

const { mocks } = vi.hoisted(() => ({
  mocks: {
    isAdmin: true,
    getCompany: vi.fn(),
    uploadCompanyWechatQr: vi.fn(),
    createObjectURL: vi.fn(),
    revokeObjectURL: vi.fn(),
    messageSuccess: vi.fn(),
    messageError: vi.fn(),
    messageWarning: vi.fn(),
  },
}))

const nativeURL = globalThis.URL

vi.mock('@/api/company', () => ({
  getCompany: mocks.getCompany,
  uploadCompanyWechatQr: mocks.uploadCompanyWechatQr,
}))
vi.mock('@/store/user', () => ({ useUserStore: () => ({ isAdmin: mocks.isAdmin }) }))
vi.mock('element-plus', () => ({
  ElMessage: {
    success: mocks.messageSuccess,
    error: mocks.messageError,
    warning: mocks.messageWarning,
  },
}))

import ContactWechatQrCard from '@/components/ContactWechatQrCard.vue'

const dialogStub = {
  props: ['modelValue', 'title'],
  template: '<div v-if="modelValue" role="dialog"><h2>{{ title }}</h2><slot /><slot name="footer" /></div>',
}
const buttonStub = {
  props: ['type', 'disabled', 'loading'],
  emits: ['click'],
  template: `<button :disabled="disabled || loading" @click="$emit('click', $event)"><slot /></button>`,
}

function mountCard() {
  return mount(ContactWechatQrCard, {
    global: {
      stubs: {
        'el-dialog': dialogStub,
        'el-button': buttonStub,
      },
    },
  })
}

function installUrlMocks() {
  const mockedUrl = class extends nativeURL {}
  Object.defineProperties(mockedUrl, {
    createObjectURL: { value: mocks.createObjectURL },
    revokeObjectURL: { value: mocks.revokeObjectURL },
  })
  vi.stubGlobal('URL', mockedUrl)
}

describe('ContactWechatQrCard', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mocks.isAdmin = true
    mocks.getCompany.mockResolvedValue({ data: { wechatQrCode: null } })
    mocks.uploadCompanyWechatQr.mockResolvedValue({ data: { wechatQrCode: '/media/company/contact/wechat-new.png' } })
    mocks.createObjectURL.mockReturnValue('blob:wechat-preview')
    installUrlMocks()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('显示已配置的联系二维码，普通员工没有上传入口', async () => {
    mocks.isAdmin = false
    mocks.getCompany.mockResolvedValue({ data: { wechatQrCode: '/media/company/contact/wechat.png' } })

    const wrapper = mountCard()
    await flushPromises()

    expect(wrapper.text()).toContain('联系客服')
    expect(wrapper.find('img').attributes('src')).toBe('/media/company/contact/wechat.png')
    expect(wrapper.find('.qr-trigger').exists()).toBe(false)
  })

  it('管理员选图后先预览，确认后才上传并显示新二维码', async () => {
    const wrapper = mountCard()
    await flushPromises()
    const file = new File(['qr'], 'wechat.png', { type: 'image/png' })
    const input = wrapper.get('input[type="file"]')

    await wrapper.get('.qr-trigger').trigger('click')
    Object.defineProperty(input.element, 'files', { value: [file], configurable: true })

    await input.trigger('change')
    await flushPromises()

    expect(wrapper.get('[role="dialog"]').text()).toContain('确认更换客服二维码')
    expect(wrapper.get('.qr-preview img').attributes('src')).toBe('blob:wechat-preview')
    expect(mocks.uploadCompanyWechatQr).not.toHaveBeenCalled()

    await wrapper.get('.confirm-replace').trigger('click')
    await flushPromises()

    expect(mocks.uploadCompanyWechatQr).toHaveBeenCalledWith(file)
    expect(wrapper.get('.qr-trigger img').attributes('src')).toBe('/media/company/contact/wechat-new.png')
    expect(wrapper.find('[role="dialog"]').exists()).toBe(false)
    expect(mocks.revokeObjectURL).toHaveBeenCalledWith('blob:wechat-preview')
  })

  it('取消预览不会上传或替换已有二维码', async () => {
    mocks.getCompany.mockResolvedValue({ data: { wechatQrCode: '/media/company/contact/wechat.png' } })
    const wrapper = mountCard()
    await flushPromises()
    const file = new File(['new qr'], 'wechat-new.png', { type: 'image/png' })
    const input = wrapper.get('input[type="file"]')

    await wrapper.get('.qr-trigger').trigger('click')
    Object.defineProperty(input.element, 'files', { value: [file], configurable: true })
    await input.trigger('change')
    await flushPromises()
    await wrapper.get('.cancel-preview').trigger('click')

    expect(wrapper.find('[role="dialog"]').exists()).toBe(false)
    expect(wrapper.get('.qr-trigger img').attributes('src')).toBe('/media/company/contact/wechat.png')
    expect(mocks.uploadCompanyWechatQr).not.toHaveBeenCalled()
    expect(mocks.revokeObjectURL).toHaveBeenCalledWith('blob:wechat-preview')
  })
})
