<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import { useUserStore } from '@/store/user'

const userStore = useUserStore()

onMounted(() => {
  if (userStore.isLoggedIn) {
    userStore.startTokenExpiryCheck()
  }
})

onUnmounted(() => {
  userStore.cleanup()
})
</script>

<template>
  <router-view />
</template>
