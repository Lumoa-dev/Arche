<template>
  <div class="page-shell">
    <ArPageHeader title="调度器" desc="管理模型训练任务与爬虫调度" />
    <div class="placeholder-card">
      <p>调度器功能开发中，敬请期待</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import ArPageHeader from '@/components/ui/ArPageHeader.vue'
</script>

<style scoped>
.page-shell {
  width: min(900px, 100%);
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: var(--layout-gap);
}

.placeholder-card {
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: var(--spacing-3xl);
  text-align: center;
  color: var(--text-tertiary);
}
</style>
