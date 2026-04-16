<script setup lang="ts">
import { getSystemAvatarSvg, hasSystemAvatar } from '@/utils/avatar'

defineProps<{
  modelValue?: string | null
  disabled?: boolean
}>()

const emit = defineEmits<{
  select: [key: string]
  upload: []
}>()

const avatarKeys = Array.from({ length: 10 }, (_, i) => `geo-${i + 1}`)

function handleSelect(key: string) {
  emit('select', key)
}
</script>

<template>
  <div class="system-avatars">
    <div class="avatar-label">选择头像</div>
    <div class="avatar-grid">
      <button
        v-for="key in avatarKeys"
        :key="key"
        class="avatar-item"
        :class="{ selected: modelValue === key && !disabled }"
        :disabled="disabled"
        @click="handleSelect(key)"
        v-html="getSystemAvatarSvg(key, 48)"
      />
      <button class="avatar-item upload-btn" :disabled="disabled" @click="emit('upload')">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="12" y1="5" x2="12" y2="19"/>
          <line x1="5" y1="12" x2="19" y2="12"/>
        </svg>
      </button>
    </div>
  </div>
</template>

<style scoped>
.system-avatars {
  padding: 0;
}

.avatar-label {
  font-size: 13px;
  font-weight: 500;
  color: rgba(0, 0, 0, 0.65);
  margin-bottom: 10px;
}

.avatar-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 8px;
}

.avatar-item {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  border: 2px solid transparent;
  background: transparent;
  cursor: pointer;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s ease;
  overflow: hidden;
}

.avatar-item:hover:not(:disabled) {
  border-color: var(--color-primary-200);
  transform: scale(1.05);
}

.avatar-item.selected {
  border-color: var(--color-primary-500);
  box-shadow: 0 0 0 2px var(--color-primary-100);
}

.avatar-item:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.avatar-item :deep(svg) {
  border-radius: 50%;
}

.upload-btn {
  background: var(--color-bg-elevated);
  border: 2px dashed var(--color-border);
  color: rgba(0, 0, 0, 0.35);
}

.upload-btn:hover:not(:disabled) {
  border-color: var(--color-primary-300);
  color: var(--color-primary-500);
  background: var(--color-primary-50);
}

.upload-btn svg {
  width: 20px;
  height: 20px;
}
</style>
