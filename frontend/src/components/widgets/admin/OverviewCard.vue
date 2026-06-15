<script setup lang="ts">
import type { Component } from 'vue'
import { NIcon } from 'naive-ui'
import { useRouter } from 'vue-router'

const props = defineProps<{
  title: string
  icon?: Component
  to: string | null
  disabled?: boolean
  stats: { label: string; value: string | number }[]
  note?: string
}>()

const router = useRouter()

function handleClick() {
  if (props.to) router.push(props.to)
}
</script>

<template>
  <div
    class="overview-card"
    :class="{ 'card-disabled': disabled || !to }"
    @click="handleClick"
  >
    <div class="card-header">
      <NIcon v-if="icon" size="22" class="card-icon"><component :is="icon" /></NIcon>
      <h3 class="card-title">{{ title }}</h3>
    </div>
    <div class="card-stats">
      <div v-for="stat in stats" :key="stat.label" class="stat">
        <span class="stat-value">{{ stat.value }}</span>
        <span class="stat-label">{{ stat.label }}</span>
      </div>
    </div>
    <p v-if="note" class="card-note">{{ note }}</p>
  </div>
</template>

<style scoped>
.overview-card {
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 20px;
  cursor: pointer;
  transition: all var(--transition-fast);
}
.overview-card:hover {
  border-color: var(--primary-color);
  transform: translateY(-1px);
}
.card-disabled {
  opacity: 0.6;
  cursor: default;
}
.card-disabled:hover {
  border-color: var(--border-color);
  transform: none;
}
.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
}
.card-icon {
  color: var(--primary-color);
}
.card-title {
  margin: 0;
  font-size: 16px;
  font-weight: var(--font-weight-semibold);
  color: var(--text-primary);
}
.card-stats {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.stat {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.stat-value {
  font-size: 18px;
  font-weight: var(--font-weight-bold);
  color: var(--text-primary);
}
.stat-label {
  font-size: 13px;
  color: var(--text-secondary);
}
.card-note {
  margin: 12px 0 0;
  font-size: 12px;
  color: var(--text-tertiary);
}
</style>
