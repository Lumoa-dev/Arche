<script setup lang="ts">
/**
 * PostStatsCards — 统计卡片组
 *
 * 展示全部文章、已发布、草稿、总阅读 4 张统计卡片。
 * 图标根据 label 映射，数据由父组件通过 statCards 传入。
 */
import { type Component } from 'vue'
import { NIcon } from 'naive-ui'
import { DocumentTextOutline, EyeOutline, CreateOutline, HeartOutline } from '@vicons/ionicons5'
import type { StatCard } from '@/components/logic/usePostManager'

defineProps<{
  statCards: StatCard[]
}>()

const iconMap: Record<string, Component> = {
  全部文章: DocumentTextOutline,
  已发布: EyeOutline,
  草稿: CreateOutline,
  总阅读: HeartOutline
}

function getIcon(label: string): Component {
  return iconMap[label] || DocumentTextOutline
}
</script>

<template>
  <div class="stats-grid">
    <div v-for="card in statCards" :key="card.label" class="stat-card">
      <div class="stat-icon" :style="{ background: card.color + '14', color: card.color }">
        <NIcon :size="20">
          <component :is="getIcon(card.label)" />
        </NIcon>
      </div>
      <div class="stat-body">
        <span class="stat-value">{{ card.value }}</span>
        <span class="stat-label">{{ card.label }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 14px;
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: var(--spacing-lg);
}

.stat-icon {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.stat-body {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.stat-value {
  font-size: 22px;
  font-weight: var(--font-weight-bold);
  color: var(--text-primary);
  line-height: 1;
}

.stat-label {
  font-size: 12px;
  color: var(--text-tertiary);
}

@media (max-width: 768px) {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
