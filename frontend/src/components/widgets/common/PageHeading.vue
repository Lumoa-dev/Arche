<script setup lang="ts">
/**
 * PageHeading — 页面标题栏
 *
 * 标题 + 可选的右侧操作区域。
 * 页面 0 CSS：本组件承载所有标题栏样式。
 */
defineProps<{
  title: string
}>()
</script>

<template>
  <div class="page-heading">
    <h2 class="page-heading__title">{{ title }}</h2>
    <div class="page-heading__actions">
      <slot name="actions" />
    </div>
  </div>
</template>

<style scoped>
.page-heading {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-lg);
}

.page-heading__title {
  margin: 0;
  font-size: 24px;
  font-weight: var(--font-weight-bold);
  color: var(--text-primary);
}

.page-heading__actions {
  display: flex;
  gap: var(--spacing-sm);
  align-items: center;
}
</style>
