<script setup lang="ts">
import { useRouter } from 'vue-router'
import type { Component } from 'vue'
import { NIcon } from 'naive-ui'
import { DocumentTextOutline, ChatbubblesOutline, WarningOutline } from '@vicons/ionicons5'

const router = useRouter()

interface StatItem {
  label: string
  value: string | number
}

interface CardItem {
  title: string
  icon: Component
  stats: StatItem[]
  to: string
  note?: string
}

// Router stubs
// /admin/content/comments — 暂未实现
// /admin/content/reports  — 暂未实现

const cards: CardItem[] = [
  {
    title: '帖子审核',
    icon: DocumentTextOutline,
    stats: [
      { label: '待审核', value: 7 },
      { label: '今日通过', value: 12 },
      { label: '今日驳回', value: 3 }
    ],
    to: '/admin/content/moderation'
  },
  {
    title: '评论管理',
    icon: ChatbubblesOutline,
    stats: [
      { label: '待审核评论', value: 5 },
      { label: '举报待处理', value: 2 }
    ],
    to: '/admin/content/comments',
    note: '暂未实现'
  },
  {
    title: '举报处理',
    icon: WarningOutline,
    stats: [
      { label: '待处理举报', value: 2 },
      { label: '今日新增', value: 1 }
    ],
    to: '/admin/content/reports',
    note: '暂未实现'
  }
]

const navigate = (to: string) => {
  router.push(to)
}
</script>

<template>
  <div class="overview-page">
    <h1 class="page-title">{{ $route.meta.title }}</h1>
    <div class="card-grid card-grid--3col">
      <div v-for="card in cards" :key="card.title" class="overview-card" @click="navigate(card.to)">
        <div class="card-header">
          <NIcon size="28" class="card-icon"><component :is="card.icon" /></NIcon>
          <span class="card-title">{{ card.title }}</span>
          <span v-if="card.note" class="card-note">{{ card.note }}</span>
        </div>
        <div class="card-stats">
          <div v-for="stat in card.stats" :key="stat.label" class="stat-item">
            <span class="stat-value">{{ stat.value }}</span>
            <span class="stat-label">{{ stat.label }}</span>
          </div>
        </div>
        <div class="card-action">
          <span>进入管理</span>
          <span class="action-arrow">→</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.overview-page {
  max-width: 100%;
}

.page-title {
  margin: 0 0 var(--spacing-lg);
  font-size: 22px;
  font-weight: var(--font-weight-bold);
  color: var(--text-primary);
}

.card-grid {
  display: grid;
  gap: var(--spacing-md);
}

.card-grid--3col {
  grid-template-columns: repeat(3, 1fr);
}

.overview-card {
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: var(--spacing-lg);
  cursor: pointer;
  transition: all var(--transition-normal);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
  backdrop-filter: blur(4px);
}

.overview-card:hover {
  box-shadow: var(--shadow-md);
  border-color: var(--primary-color);
  transform: translateY(-2px);
}

.card-header {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.card-icon {
  color: var(--primary-color);
  flex-shrink: 0;
}

.card-title {
  font-size: 16px;
  font-weight: var(--font-weight-semibold);
  color: var(--text-primary);
}

.card-note {
  font-size: 11px;
  color: var(--text-tertiary);
  background: var(--surface-inset-color);
  padding: 2px 8px;
  border-radius: var(--radius-sm);
  margin-left: auto;
}

.card-stats {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--spacing-sm);
}

.card-stats:has(> :nth-child(3)) {
  grid-template-columns: repeat(3, 1fr);
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  padding: var(--spacing-sm) 0;
  background: var(--surface-inset-color);
  border-radius: var(--radius-sm);
}

.stat-value {
  font-size: 20px;
  font-weight: var(--font-weight-bold);
  color: var(--text-primary);
  line-height: 1.2;
}

.stat-label {
  font-size: 12px;
  color: var(--text-tertiary);
}

.card-action {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: var(--spacing-sm);
  border-top: 1px solid var(--border-color);
  font-size: 13px;
  font-weight: var(--font-weight-medium);
  color: var(--primary-color);
  transition: all var(--transition-fast);
}

.overview-card:hover .card-action {
  color: var(--primary-hover-color);
}

.action-arrow {
  font-size: 16px;
  transition: transform var(--transition-fast);
}

.overview-card:hover .action-arrow {
  transform: translateX(4px);
}

/* 响应式 */
@media (max-width: 992px) {
  .card-grid--3col {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 600px) {
  .card-grid--3col {
    grid-template-columns: 1fr;
  }
}
</style>
