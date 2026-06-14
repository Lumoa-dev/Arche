<script setup lang="ts">
/**
 * PostIntro — 文章引言区（摘要 + 关键点 + 阅读时间 + 难度）
 */
defineProps<{
  abstract?: string
  keyPoints?: string[]
  readingTime?: number
  difficultyLevel?: string
}>()
</script>

<template>
  <div v-if="abstract || keyPoints?.length || readingTime" class="post-intro">
    <p v-if="abstract" class="post-intro__abstract">{{ abstract }}</p>
    <div v-if="keyPoints?.length" class="post-intro__key-points">
      <span v-for="point in keyPoints" :key="point" class="key-point">{{ point }}</span>
    </div>
    <div v-if="readingTime || difficultyLevel" class="post-intro__meta">
      <span v-if="readingTime" class="reading-time">{{ readingTime }} 分钟阅读</span>
      <span v-if="difficultyLevel" class="difficulty">{{ difficultyLevel }}</span>
    </div>
  </div>
</template>

<style scoped>
.post-intro {
  margin: var(--spacing-md) 0 var(--spacing-lg);
  padding: var(--spacing-md);
  background: var(--surface-hover-color, rgba(128, 128, 128, 0.04));
  border-radius: var(--radius-sm);
  border-left: 3px solid var(--primary-color);
}

.post-intro__abstract {
  font-size: 14px;
  line-height: 1.7;
  color: var(--text-secondary);
  margin: 0 0 var(--spacing-sm);
}

.post-intro__key-points {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: var(--spacing-sm);
}

.key-point {
  display: inline-flex;
  align-items: center;
  padding: 2px 10px;
  font-size: 12px;
  color: var(--primary-color);
  background: var(--primary-light-color, rgba(102, 126, 234, 0.08));
  border-radius: var(--radius-full);
  font-weight: var(--font-weight-medium);
}

.post-intro__meta {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  font-size: 12px;
  color: var(--text-tertiary);
}
</style>
