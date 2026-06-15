<script setup lang="ts">
/**
 * StatCard — 统计卡片（用于管理后台仪表盘）
 */
defineProps<{
  label: string
  value: string | number
}>()
</script>

<template>
  <div class="stat-card">
    <div class="stat-value">{{ value }}</div>
    <div class="stat-label">{{ label }}</div>
  </div>
</template>

<style scoped>
.stat-card {
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 20px;
  gap: 6px;
}
.stat-label {
  font-size: 14px;
  color: var(--text-secondary);
}
.stat-value {
  font-size: 24px;
  font-weight: var(--font-weight-bold);
  color: var(--text-primary);
}
</style>
