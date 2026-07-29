<script setup lang="ts">
withDefaults(defineProps<{
  size?: number | string
  variant?: 'mono' | 'brand'
  hideText?: boolean
}>(), {
  size: 32,
  variant: 'mono',
  hideText: true,
})
</script>

<template>
  <span class="brand-logo">
    <svg
      :width="size"
      :height="size"
      viewBox="0 0 48 48"
      fill="none"
      :class="['logo-svg', variant]"
      aria-hidden="true"
    >
      <!-- 资产层叠：三层堆叠的盒/箱 -->
      <rect class="layer layer-1" x="8" y="30" width="32" height="11" rx="2.5" />
      <rect class="layer layer-2" x="8" y="18.5" width="32" height="11" rx="2.5" />
      <rect class="layer layer-3" x="8" y="7" width="32" height="11" rx="2.5" />
      <!-- 勾选：盘点完成（仅 brand 版） -->
      <path
        v-if="variant === 'brand'"
        class="check"
        d="M20 12.5l2.8 2.8L28 10"
        stroke-width="2.4"
        stroke-linecap="round"
        stroke-linejoin="round"
      />
    </svg>
    <span v-if="!hideText" class="logo-text">磐盘</span>
  </span>
</template>

<style scoped>
.brand-logo {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
}

/* mono 版：随 currentColor，层叠透明度递进（适配侧边栏 / favicon 单色场景） */
.logo-svg.mono .layer { fill: currentColor; }
.logo-svg.mono .layer-1 { opacity: 0.35; }
.logo-svg.mono .layer-2 { opacity: 0.65; }
.logo-svg.mono .layer-3 { opacity: 1; }

/* brand 版：品牌蓝渐变 + 白色勾选（登录页强调场景） */
.logo-svg.brand .layer-1 { fill: var(--color-primary-300); }
.logo-svg.brand .layer-2 { fill: var(--color-primary-500); }
.logo-svg.brand .layer-3 { fill: var(--color-primary-600); }
.logo-svg.brand .check { stroke: #fff; }

.logo-text {
  font-size: 1.25rem;
  font-weight: 700;
  color: currentColor;
  letter-spacing: 0.04em;
  white-space: nowrap;
}
</style>
