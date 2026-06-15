<script setup lang="ts">
import { NIcon } from 'naive-ui'
import type { Component } from 'vue'

defineProps<{
  title: string
  icon: Component
  iconColor: string
  stats: { label: string; value: string | number }[]
  actionText?: string
}>()

const emit = defineEmits<{
  click: []
}>()
</script>

<template>
  <div class="task-card" @click="emit('click')">
    <div class="card-header">
      <NIcon size="28" class="card-icon" :style="{ background: iconColor.replace(')', ', 0.1)').replace('rgb', 'rgba'), color: iconColor }"><component :is="icon" /></NIcon>
      <span class="card-title">{{ title }}</span>
    </div>
    <div class="card-stats">
      <div v-for="stat in stats" :key="stat.label" class="stat-item">
        <span class="stat-value">{{ stat.value }}</span>
        <span class="stat-label">{{ stat.label }}</span>
      </div>
    </div>
    <button v-if="actionText" class="card-action">{{ actionText }}</button>
  </div>
</template>

<style scoped>
.task-card {
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 24px;
  cursor: pointer;
  transition: all 0.2s ease;
}
.task-card:hover {
  box-shadow: var(--shadow-md);
  border-color: var(--primary-color);
  transform: translateY(-2px);
}
.card-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}
.card-icon {
  padding: 10px;
  border-radius: var(--radius-sm);
}
.card-title {
  font-size: 17px;
  font-weight: 600;
  color: var(--text-primary);
}
.card-stats {
  display: flex;
  gap: 20px;
  margin-bottom: 20px;
}
.stat-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.stat-value {
  font-size: 20px;
  font-weight: 700;
  color: var(--text-primary);
}
.stat-label {
  font-size: 12px;
  color: var(--text-tertiary);
}
.card-action {
  width: 100%;
  padding: 10px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--text-secondary);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s ease;
  font-family: inherit;
}
.card-action:hover {
  background: var(--primary-light-color);
  color: var(--primary-color);
  border-color: var(--primary-color);
}
</style>
