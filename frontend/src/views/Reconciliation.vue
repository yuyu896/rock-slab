<script setup lang="ts">
// 对账模块占位页（reconciliation-nav-placeholder）：
// 业务本体（租赁设备供应商账单序列号核对）另行专门立项，本页留白。
</script>

<template>
  <div class="reconciliation-page page-fill">
    <div class="page-header">
      <div class="header-info">
        <h1 class="page-title">对账</h1>
      </div>
    </div>
  </div>
</template>

<style scoped>
.reconciliation-page { max-width: 1600px; margin: 0 auto; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: var(--space-5); flex-shrink: 0; }
.header-info { display: flex; flex-direction: column; gap: var(--space-1); }
.page-title { font-size: var(--text-xl); font-weight: 600; margin: 0; }
</style>
