<script setup lang="ts">
import { ref, watch } from 'vue'

const props = withDefaults(defineProps<{
  total: number
  currentPage: number
  pageSize?: number
  pageSizes?: number[]
}>(), {
  pageSize: 20,
  pageSizes: () => [10, 20, 50, 100],
})

const emit = defineEmits<{
  (e: 'change', page: number, pageSize: number): void
}>()

const internalPage = ref(props.currentPage)
const internalPageSize = ref(props.pageSize)

watch(() => props.currentPage, v => internalPage.value = v)
watch(() => props.pageSize, v => internalPageSize.value = v)

function handleCurrentChange(page: number) {
  emit('change', page, internalPageSize.value)
}

function handleSizeChange(size: number) {
  emit('change', 1, size)
}
</script>

<template>
  <div class="base-pagination">
    <el-pagination
      v-model:current-page="internalPage"
      v-model:page-size="internalPageSize"
      :page-sizes="pageSizes"
      :total="total"
      layout="total, sizes, prev, pager, next, jumper"
      background
      @current-change="handleCurrentChange"
      @size-change="handleSizeChange"
    />
  </div>
</template>

<style scoped>
.base-pagination {
  display: flex;
  justify-content: flex-end;
  padding: 16px 0;
}
</style>
