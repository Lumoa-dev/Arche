<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    postId: string
    authorUsername?: string
    sourceUrl?: string
    sourceName?: string
  }>(),
  {
    authorUsername: '',
    sourceUrl: '',
    sourceName: ''
  }
)

const shortId = computed(() => {
  const raw = props.postId.replace(/-/g, '')
  return '#' + raw.slice(0, 8).toUpperCase()
})

const authorInitial = computed(() => {
  return (props.authorUsername || '?').charAt(0).toUpperCase()
})

const hasSource = computed(() => props.sourceUrl && props.sourceName)
</script>

<template>
  <div :class="['author-bar', { 'has-source': hasSource }]">
    <!-- 左侧：文章短 ID -->
    <span class="post-id">{{ shortId }}</span>

    <!-- 右侧：作者信息 -->
    <div class="author-info">
      <div class="author-avatar">{{ authorInitial }}</div>
      <span class="author-name">{{ authorUsername || '匿名' }}</span>
    </div>

    <!-- 转载来源（仅在有时显示） -->
    <a
      v-if="hasSource"
      :href="sourceUrl"
      class="source-link"
      target="_blank"
      rel="noopener noreferrer"
    >
      转载自 {{ sourceName }}
    </a>
  </div>
</template>

<style scoped>
.author-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-md) 0;
  border-bottom: 1px solid var(--divider-color);
  margin-bottom: var(--spacing-lg);
}

/* ── 左侧 ID ── */
.post-id {
  font-family: var(--font-mono, var(--font-sans));
  font-size: 13px;
  color: var(--text-tertiary);
  letter-spacing: 0.02em;
  user-select: all;
}

/* ── 右侧作者 ── */
.author-info {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.author-avatar {
  width: 32px;
  height: 32px;
  border-radius: var(--radius-full);
  background: var(--primary-light-color);
  color: var(--primary-color);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: var(--font-weight-semibold);
  user-select: none;
  flex-shrink: 0;
}

.author-name {
  font-size: 14px;
  font-weight: var(--font-weight-medium);
  color: var(--text-primary);
}

/* ── 转载来源 ── */
.source-link {
  font-size: 12px;
  color: var(--text-tertiary);
  text-decoration: none;
  padding: 2px 8px;
  border-radius: var(--radius-sm);
  background: var(--surface-inset-color);
  transition: color var(--transition-fast);
  white-space: nowrap;
}

.source-link:hover {
  color: var(--primary-color);
}

.has-source .author-info {
  /* 有来源时，作者往左挪，给来源让位 */
  margin-right: auto;
  margin-left: var(--spacing-xl);
}
</style>
