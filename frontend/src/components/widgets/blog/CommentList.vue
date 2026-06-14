<script setup lang="ts">
import type { BlogComment } from '@/components/logic/api'

defineProps<{
  comments: BlogComment[]
}>()

function authorInitial(username?: string): string {
  return ((username || '?')[0] || '').toUpperCase()
}

function formatDate(dateStr?: string): string {
  return dateStr?.slice(0, 10) || '-'
}
</script>

<template>
  <div class="comment-list">
    <div v-if="comments.length === 0" class="comment-empty">
      <span>暂无评论</span>
    </div>

    <div v-for="comment in comments" :key="comment.id" class="comment-item">
      <div class="comment-avatar">
        {{ authorInitial(comment.author_username) }}
      </div>
      <div class="comment-body">
        <div class="comment-header">
          <span class="comment-user">{{ comment.author_username || '匿名' }}</span>
          <span class="comment-time">{{ formatDate(comment.created_at) }}</span>
        </div>
        <div class="comment-content">{{ comment.content }}</div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.comment-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-lg);
}

.comment-empty {
  text-align: center;
  padding: var(--spacing-2xl) 0;
  font-size: 14px;
  color: var(--text-tertiary);
}

.comment-item {
  display: flex;
  gap: var(--spacing-sm);
}

.comment-avatar {
  width: 34px;
  height: 34px;
  border-radius: var(--radius-full);
  background: var(--primary-light-color);
  color: var(--primary-color);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: var(--font-weight-semibold);
  flex-shrink: 0;
  user-select: none;
}

.comment-body {
  flex: 1;
  min-width: 0;
}

.comment-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  margin-bottom: 4px;
}

.comment-user {
  font-size: 13px;
  font-weight: var(--font-weight-semibold);
  color: var(--text-primary);
}

.comment-time {
  font-size: 11px;
  color: var(--text-tertiary);
  margin-left: auto;
  white-space: nowrap;
}

.comment-content {
  font-size: 14px;
  line-height: 1.6;
  color: var(--text-primary);
  white-space: pre-wrap;
  word-break: break-word;
}
</style>
