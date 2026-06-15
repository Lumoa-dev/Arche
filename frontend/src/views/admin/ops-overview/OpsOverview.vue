<script setup lang="ts">
import { useRouter } from 'vue-router'
import type { Component } from 'vue'
import { NIcon } from 'naive-ui'
import {
  PulseOutline,
  SettingsOutline,
  CloudOutline,
  ShieldCheckmarkOutline,
  ExtensionPuzzleOutline,
  ServerOutline
} from '@vicons/ionicons5'

const router = useRouter()

interface StatItem {
  label: string
  value: string | number
}

interface CardItem {
  title: string
  icon: Component
  stats: StatItem[]
  to: string | null
  note?: string
}

// Router stubs
// /admin/ops/permissions — 暂无（占位）
// /admin/ops/plugins     — 暂未实现，后端未实现
// /admin/ops/logs        — 暂未实现，后端未实现

const cards: CardItem[] = [
  {
    title: '系统监控',
    icon: PulseOutline,
    stats: [
      { label: 'CPU', value: '23%' },
      { label: '内存', value: '45%' },
      { label: '磁盘', value: '67%' }
    ],
    to: '/admin/ops/system'
  },
  {
    title: '运行时配置',
    icon: SettingsOutline,
    stats: [
      { label: '已配置', value: '12 项' },
      { label: '系统默认', value: '8 项' }
    ],
    to: '/admin/ops/config'
  },
  {
    title: 'OSS 存储管理',
    icon: CloudOutline,
    stats: [
      { label: '总存储', value: '2.1 TB' },
      { label: '已用', value: '1.2 TB' },
      { label: '用户', value: '128 人' }
    ],
    to: '/admin/ops/storage'
  },
  {
    title: '权限管理',
    icon: ShieldCheckmarkOutline,
    stats: [
      { label: '等级', value: 'P0~P5' },
      { label: '权限规则', value: '24 条' }
    ],
    to: null,
    note: '暂无'
  },
  {
    title: '插件管理',
    icon: ExtensionPuzzleOutline,
    stats: [
      { label: '已安装', value: 8 },
      { label: '已启用', value: 6 }
    ],
    to: null,
    note: '暂未实现，后端未实现'
  },
  {
    title: '日志管理',
    icon: ServerOutline,
    stats: [
      { label: '今日日志', value: '234 条' },
      { label: '错误', value: '3 条' }
    ],
    to: null,
    note: '暂未实现，后端未实现'
  }
]

const navigate = (to: string | null) => {
  if (to) router.push(to)
}
</script>

<template>
  <div class="overview-page">
    <h1 class="page-title">{{ $route.meta.title }}</h1>
    <div class="card-grid card-grid--3x2">
      <div
        v-for="card in cards"
        :key="card.title"
        class="overview-card"
        :class="{ 'card-disabled': !card.to }"
        @click="navigate(card.to)"
      >
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
          <span>{{ card.to ? '进入管理' : '暂不可用' }}</span>
          <span v-if="card.to" class="action-arrow">→</span>
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

.card-grid--3x2 {
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

.overview-card.card-disabled {
  cursor: default;
  opacity: 0.7;
}

.overview-card.card-disabled:hover {
  box-shadow: none;
  border-color: var(--border-color);
  transform: none;
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

.card-disabled .card-icon {
  color: var(--text-tertiary);
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
  gap: var(--spacing-sm);
  grid-template-columns: repeat(2, 1fr);
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

.card-disabled .card-action {
  color: var(--text-tertiary);
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
  .card-grid--3x2 {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 600px) {
  .card-grid--3x2 {
    grid-template-columns: 1fr;
  }
}
</style>
