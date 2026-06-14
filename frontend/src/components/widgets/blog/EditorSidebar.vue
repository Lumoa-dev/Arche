<script setup lang="ts">
/**
 * EditorSidebar — 编辑模式侧边栏帖子列表
 *
 * 显示所有帖子的标题、状态圆点和日期，支持点击切换编辑目标。
 */
import type { BlogPost } from '@/components/logic/api'

defineProps<{
  posts: BlogPost[]
  activePostId: string | null
}>()

const emit = defineEmits<{
  select: [post: BlogPost]
  back: []
}>()

function handleClick(post: BlogPost) {
  emit('select', post)
}
</script>

<template>
  <aside class="edit-sidebar">
    <button class="sidebar-back" @click="emit('back')">← 返回</button>
    <div class="sidebar-items">
      <button
        v-for="p in posts"
        :key="p.id"
        class="sidebar-item"
        :class="{ active: p.id === activePostId }"
        @click="handleClick(p)"
      >
        <div class="sidebar-item-title">{{ p.title || '无标题' }}</div>
        <div class="sidebar-item-meta">
          <span class="sidebar-item-status" :class="p.status || 'draft'"></span>
          <span>{{ p.created_at?.slice(0, 10) || '' }}</span>
        </div>
      </button>
    </div>
  </aside>
</template>

<style scoped>
.edit-sidebar {
  width: 220px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  border-right: 1px solid var(--border-color);
  background: var(--bg-inset-color);
}

.sidebar-back {
  border: 0;
  border-bottom: 1px solid var(--border-color);
  background: transparent;
  padding: 14px 16px;
  font-size: 14px;
  font-family: var(--font-sans);
  color: var(--text-primary);
  cursor: pointer;
  text-align: left;
  font-weight: var(--font-weight-medium);
  transition: background var(--transition-fast);
  flex-shrink: 0;
}

.sidebar-back:hover {
  background: var(--surface-strong-color);
}

.sidebar-items {
  flex: 1;
  overflow-y: auto;
  padding: 4px 0;
}

.sidebar-item {
  display: block;
  width: 100%;
  border: 0;
  border-left: 3px solid transparent;
  background: transparent;
  padding: 12px 16px;
  text-align: left;
  cursor: pointer;
  transition: all var(--transition-fast);
  font-family: var(--font-sans);
}

.sidebar-item:hover {
  background: var(--surface-hover-color);
  border-left-color: var(--border-color);
}

.sidebar-item.active {
  background: var(--primary-light-color);
  border-left-color: var(--primary-color);
}

.sidebar-item-title {
  font-size: 14px;
  color: var(--text-primary);
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
  font-weight: var(--font-weight-medium);
}

.sidebar-item.active .sidebar-item-title {
  color: var(--primary-color);
}

.sidebar-item-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 4px;
  font-size: 12px;
  color: var(--text-tertiary);
}

.sidebar-item-status {
  display: inline-block;
  width: 6px;
  height: 6px;
  border-radius: 50%;
}

.sidebar-item-status.published {
  background: var(--success-color);
}

.sidebar-item-status.draft {
  background: var(--accent-yellow);
}

.sidebar-item-status.pending {
  background: var(--accent-orange, #e8a817);
}

@media (max-width: 768px) {
  .edit-sidebar {
    width: 160px;
  }
}
</style>
