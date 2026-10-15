<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getCompany, uploadCompanyWechatQr } from '@/api/company'
import { useUserStore } from '@/store/user'
import { handleApiError } from '@/utils/request'

const userStore = useUserStore()
const qrCodeUrl = ref<string | null>(null)
const loaded = ref(false)
const uploading = ref(false)
const previewVisible = ref(false)
const previewUrl = ref<string | null>(null)
const selectedFile = ref<File | null>(null)
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

function clearPreview() {
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
  previewUrl.value = null
  selectedFile.value = null
}

function cancelPreview() {
  if (uploading.value) return
  previewVisible.value = false
  clearPreview()
}

function selectImage(event: Event) {
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

  clearPreview()
  selectedFile.value = file
  previewUrl.value = URL.createObjectURL(file)
  previewVisible.value = true
  input.value = ''
}

async function confirmUpload() {
  const file = selectedFile.value
  if (!file || uploading.value) return

  uploading.value = true
  try {
    const { data } = await uploadCompanyWechatQr(file)
    qrCodeUrl.value = data.wechatQrCode || null
    ElMessage.success('客服二维码已更新')
    previewVisible.value = false
    clearPreview()
  } catch (error) {
    ElMessage.error(handleApiError(error))
  } finally {
    uploading.value = false
  }
}

onMounted(loadQrCode)
onUnmounted(clearPreview)
</script>

<template>
  <section class="wechat-qr-card" aria-label="联系客服">
    <div class="qr-heading">
      <h3>联系客服</h3>
    </div>
    <button
      v-if="userStore.isAdmin"
      type="button"
      class="qr-box qr-trigger"
      :disabled="!loaded || uploading"
      :aria-busy="!loaded || uploading"
      :title="qrCodeUrl ? '点击更换客服二维码' : '点击上传客服二维码'"
      :aria-label="qrCodeUrl ? '点击更换客服二维码' : '点击上传客服二维码'"
      @click="chooseImage"
    >
      <img v-if="qrCodeUrl" :src="qrCodeUrl" alt="" />
      <span v-else>{{ loaded ? '暂未上传' : '加载中' }}</span>
    </button>
    <div v-else class="qr-box" :aria-busy="!loaded">
      <img v-if="qrCodeUrl" :src="qrCodeUrl" alt="联系客服二维码" />
      <span v-else>{{ loaded ? '暂未上传' : '加载中' }}</span>
    </div>
    <input
      ref="fileInput"
      class="file-input"
      type="file"
      accept="image/jpeg,image/png,image/webp"
      @change="selectImage"
    />

    <el-dialog
      v-model="previewVisible"
      title="确认更换客服二维码"
      width="min(420px, calc(100vw - 32px))"
      :close-on-click-modal="false"
      :close-on-press-escape="false"
      :show-close="!uploading"
      @closed="clearPreview"
    >
      <div class="qr-preview">
        <img v-if="previewUrl" :src="previewUrl" alt="待更换的客服二维码预览" />
      </div>
      <template #footer>
        <el-button class="cancel-preview" :disabled="uploading" @click="cancelPreview">取消</el-button>
        <el-button class="confirm-replace" type="primary" :loading="uploading" @click="confirmUpload">
          确认更换
        </el-button>
      </template>
    </el-dialog>
  </section>
</template>

<style scoped>
.wechat-qr-card { display: flex; flex-direction: column; align-items: center; gap: 8px; width: 136px; }
.qr-heading { width: 136px; display: flex; align-items: center; justify-content: center; min-height: 24px; }
.qr-heading h3 { margin: 0; font-size: 13px; color: var(--color-text-secondary); font-weight: 500; }
.file-input { display: none; }
.qr-box { width: 88px; height: 88px; display: flex; align-items: center; justify-content: center; overflow: hidden; padding: 0; background: white; border: 1px solid var(--color-border); border-radius: 8px; }
.qr-trigger { cursor: pointer; }
.qr-trigger:hover:not(:disabled) { border-color: var(--color-primary-500); }
.qr-trigger:focus-visible { outline: 2px solid var(--color-primary-500); outline-offset: 2px; }
.qr-trigger:disabled { cursor: wait; opacity: 0.65; }
.qr-box img { display: block; width: 100%; height: 100%; object-fit: contain; }
.qr-box span { color: var(--color-text-tertiary); font-size: 12px; }
.qr-preview { display: flex; justify-content: center; }
.qr-preview img { display: block; width: min(100%, 280px); max-height: 60vh; object-fit: contain; }
</style>
