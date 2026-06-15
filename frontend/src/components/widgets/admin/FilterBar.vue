<script setup lang="ts">
/**
 * FilterBar — 过滤按钮条
 *
 * 用于管理后台的筛选标签切换。
 */
defineProps<{
  options: { label: string; value: string | null }[]
  modelValue: string | null
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string | null]
}>()
</script>

<template>
  <div class="filter-bar">
    <button
      v-for="opt in options"
      :key="opt.label ?? '__all'"
      class="filter-btn"
      :class="{ 'filter-btn--active': modelValue === opt.value }"
      @click="emit('update:modelValue', opt.value)"
    >
      {{ opt.label }}
    </button>
  </div>
</template>

<style scoped>
.filter-bar {
  display: flex;
  gap: 6px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}
.filter-btn {
  padding: 5px 14px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  background: var(--bg-color);
  color: var(--text-secondary);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.15s ease;
  font-family: inherit;
}
.filter-btn:hover {
  border-color: var(--primary-color);
  color: var(--primary-color);
}
.filter-btn--active {
  border-color: var(--primary-color);
  background: var(--primary-light-color);
  color: var(--primary-color);
  font-weight: 600;
}
</style>
