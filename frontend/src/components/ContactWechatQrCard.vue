<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { Upload } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { getCompany, uploadCompanyWechatQr } from '@/api/company'
import { useUserStore } from '@/store/user'
import { handleApiError } from '@/utils/request'

const userStore = useUserStore()
const qrCodeUrl = ref<string | null>(null)
const loaded = ref(false)
const uploading = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)
const allowedTypes = ['image/jpeg', 'image/png', 'image/webp']
const maxFileSize = 2 * 1024 * 1024

async function loadQrCode() {
  try {
    const { data } = await getCompany()
    qrCodeUrl.value = data.wechatQrCode || null
  } catch (error) {
    ElMessage.error(handleApiError(error))
  } finally {
    loaded.value = true
  }
}

function chooseImage() {
  fileInput.value?.click()
}

async function uploadImage(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return

  if (!allowedTypes.includes(file.type)) {
    ElMessage.warning('请选择 JPG、PNG 或 WebP 图片')
    input.value = ''
    return
  }
  if (file.size > maxFileSize) {
    ElMessage.warning('二维码图片不能超过 2MB')
    input.value = ''
    return
  }

  uploading.value = true
  try {
    const { data } = await uploadCompanyWechatQr(file)
    qrCodeUrl.value = data.wechatQrCode || null
    ElMessage.success('微信二维码已更新')
  } catch (error) {
    ElMessage.error(handleApiError(error))
  } finally {
    uploading.value = false
    input.value = ''
  }
}

onMounted(loadQrCode)
</script>

<template>
  <section class="wechat-qr-card" aria-label="联系微信">
    <div class="qr-heading">
      <h3>联系微信</h3>
      <button
        v-if="userStore.isAdmin"
        type="button"
        class="qr-upload-button"
        :disabled="uploading"
        :title="qrCodeUrl ? '更换微信二维码' : '上传微信二维码'"
        :aria-label="qrCodeUrl ? '更换微信二维码' : '上传微信二维码'"
        @click="chooseImage"
      >
        <Upload :size="16" />
      </button>
      <input
        ref="fileInput"
        class="file-input"
        type="file"
        accept="image/jpeg,image/png,image/webp"
        @change="uploadImage"
      />
    </div>
    <div class="qr-box" :aria-busy="!loaded || uploading">
      <img v-if="qrCodeUrl" :src="qrCodeUrl" alt="联系微信二维码" />
      <span v-else>{{ loaded ? '暂未上传' : '加载中' }}</span>
    </div>
  </section>
</template>

<style scoped>
.wechat-qr-card { display: flex; flex-direction: column; align-items: center; gap: 8px; width: 160px; }
.qr-heading { position: relative; width: 160px; display: flex; align-items: center; justify-content: center; min-height: 24px; }
.qr-heading h3 { margin: 0; font-size: 13px; color: var(--color-text-secondary); font-weight: 500; }
.qr-upload-button { position: absolute; right: 0; width: 24px; height: 24px; display: inline-flex; align-items: center; justify-content: center; padding: 0; border: 0; border-radius: 5px; background: transparent; color: var(--color-text-tertiary); cursor: pointer; }
.qr-upload-button:hover:not(:disabled) { background: var(--color-bg-elevated); color: var(--color-primary-600); }
.qr-upload-button:focus-visible { outline: 2px solid var(--color-primary-500); outline-offset: 2px; }
.qr-upload-button:disabled { cursor: wait; opacity: 0.55; }
.file-input { display: none; }
.qr-box { width: 144px; height: 144px; display: flex; align-items: center; justify-content: center; overflow: hidden; background: white; border: 1px solid var(--color-border); border-radius: 8px; }
.qr-box img { display: block; width: 100%; height: 100%; object-fit: contain; }
.qr-box span { color: var(--color-text-tertiary); font-size: 12px; }
</style>
