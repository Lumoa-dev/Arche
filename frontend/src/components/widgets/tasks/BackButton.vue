<script setup lang="ts">
defineProps<{
  to: string
}>()

import { useRouter } from 'vue-router'
const router = useRouter()
</script>

<template>
  <button class="back-link" @click="router.push(to)">← 返回任务中心</button>
</template>

<style scoped>
.back-link {
  padding: 8px 20px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--text-secondary);
  font-size: 13px;
  cursor: pointer;
  font-family: inherit;
  transition: all 0.2s ease;
}
.back-link:hover {
  background: var(--primary-light-color);
  color: var(--primary-color);
  border-color: var(--primary-color);
}
</style>
