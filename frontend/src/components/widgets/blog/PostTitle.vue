<script setup lang="ts">
/**
 * PostTitle — 文章标题 + 副标题
 */
defineProps<{
  title: string
  subtitle?: string
}>()
</script>

<template>
  <div class="post-title">
    <h1 class="post-title__heading">{{ title }}</h1>
    <p v-if="subtitle" class="post-title__subtitle">{{ subtitle }}</p>
  </div>
</template>

<style scoped>
.post-title__heading {
  margin: 0 0 var(--spacing-sm);
  font-size: 28px;
  font-weight: var(--font-weight-bold);
  line-height: 1.35;
  color: var(--text-primary);
  letter-spacing: -0.02em;
}

.post-title__subtitle {
  margin: 0 0 var(--spacing-md);
  font-size: 16px;
  line-height: 1.5;
  color: var(--text-secondary);
}
</style>
