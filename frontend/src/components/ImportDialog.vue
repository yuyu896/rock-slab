<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import type { UploadFile } from 'element-plus'

const props = defineProps<{
  visible: boolean
  title?: string
  accept?: string
  uploadAction: string
}>()

const emit = defineEmits<{
  (e: 'update:visible', val: boolean): void
  (e: 'success'): void
}>()

const fileList = ref<UploadFile[]>([])
const uploading = ref(false)
const result = ref<{ success: number; failed: number; errors: string[] } | null>(null)

function handleClose() {
  fileList.value = []
  result.value = null
  emit('update:visible', false)
}

async function handleSubmit() {
  if (!fileList.value.length) {
    ElMessage.warning('请先选择文件')
    return
  }
  uploading.value = true
  result.value = null
  try {
    const formData = new FormData()
    formData.append('file', fileList.value[0].raw!)

    const token = localStorage.getItem('rock_slab_token')
    const resp = await fetch(props.uploadAction, {
      method: 'POST',
      headers: { Authorization: `Token ${token}` },
      body: formData,
    })
    const data = await resp.json()

    if (resp.ok) {
      result.value = {
        success: data.success || data.created || 0,
        failed: data.failed || data.errors?.length || 0,
        errors: data.errors || [],
      }
      emit('success')
    } else {
      ElMessage.error(data.detail || data.error || '导入失败')
    }
  } catch (err) {
    ElMessage.error('导入失败，请检查文件格式')
  } finally {
    uploading.value = false
  }
}

function handleFileChange(file: UploadFile, files: UploadFile[]) {
  fileList.value = files.slice(-1) // Only keep last file
}
</script>

<template>
  <el-dialog
    :model-value="visible"
    :title="title || '批量导入'"
    width="500px"
    @close="handleClose"
  >
    <el-upload
      drag
      :auto-upload="false"
      :accept="accept || '.xlsx,.xls'"
      :limit="1"
      :file-list="fileList"
      @change="handleFileChange"
    >
      <el-icon style="font-size: 32px; color: var(--el-color-primary)"><upload-filled /></el-icon>
      <div style="margin-top: 8px">将文件拖到此处，或点击选择文件</div>
      <template #tip>
        <div class="el-upload__tip">仅支持 .xlsx / .xls 格式</div>
      </template>
    </el-upload>

    <div v-if="result" class="import-result">
      <el-alert type="success" :closable="false" style="margin-bottom: 8px">
        导入成功：{{ result.success }} 条
      </el-alert>
      <el-alert v-if="result.failed" type="warning" :closable="false">
        导入失败：{{ result.failed }} 条
      </el-alert>
    </div>

    <template #footer>
      <el-button @click="handleClose">取消</el-button>
      <el-button type="primary" :loading="uploading" @click="handleSubmit">
        {{ uploading ? '导入中...' : '开始导入' }}
      </el-button>
    </template>
  </el-dialog>
</template>

<script lang="ts">
import { UploadFilled } from '@element-plus/icons-vue'
export default { components: { UploadFilled } }
</script>

<style scoped>
.import-result {
  margin-top: 16px;
}
</style>
