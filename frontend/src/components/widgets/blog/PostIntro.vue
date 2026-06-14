<script setup lang="ts">
/**
 * PostIntro — 文章引言区（富文本渲染）
 *
 * 统一渲染引言内容，无边框无背景，与正文自然衔接。
 */
defineProps<{
  content?: string
}>()
</script>

<template>
  <div v-if="content" class="post-intro" v-html="content" />
</template>

<style scoped>
.post-intro {
  margin: var(--spacing-md) 0 var(--spacing-lg);
  padding: var(--spacing-sm) 0;
  font-size: 1.05em;
  line-height: 1.7;
  color: var(--text-secondary);
  font-family: var(--font-serif);
  border-bottom: 1px solid var(--border-color);
}

.post-intro :deep(p) {
  margin: 0;
}
</style>
