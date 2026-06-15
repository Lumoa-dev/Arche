<script setup lang="ts">
import { useRouter } from 'vue-router'
import { NButton } from 'naive-ui'
import ArCard from '@/components/ui/ArCard.vue'

defineProps<{
  code: string
  message: string
}>()

const router = useRouter()

const goBack = () => {
  router.back()
}

const goHome = () => {
  router.push('/')
}
</script>

<template>
  <div class="error-page">
    <ArCard variant="elevated" padding="lg" class="error-card">
      <h1 class="error-code">{{ code }}</h1>
      <p class="error-message">{{ message }}</p>
      <div class="error-actions">
        <NButton @click="goBack"> 返回上一页 </NButton>
        <NButton type="primary" @click="goHome"> 回到首页 </NButton>
      </div>
    </ArCard>
  </div>
</template>

<style scoped>
.error-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-xl);
}

.error-card {
  width: min(480px, 100%);
  text-align: center;
}

.error-code {
  margin: 0 0 var(--spacing-md);
  font-size: 56px;
  color: var(--text-primary);
}

.error-message {
  margin: 0 0 var(--spacing-lg);
  color: var(--text-secondary);
}

.error-actions {
  display: flex;
  justify-content: center;
  gap: var(--spacing-md);
}
</style>
