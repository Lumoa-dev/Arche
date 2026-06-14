<script setup lang="ts">
import ParagraphComponent from './ParagraphComponent.vue'
import type { ParagraphData } from '@/components/logic/api'

defineProps<{
  paragraphs: ParagraphData[]
}>()

function handleParagraphClick(para: ParagraphData) {
  // 段落点击事件预留（后续评论功能恢复时使用）
}
</script>

<template>
  <article class="post-detail">
    <ParagraphComponent
      v-for="para in paragraphs"
      :key="para.pid"
      :paragraph="para"
      @click="handleParagraphClick"
    />
  </article>
</template>

<style scoped>
.post-detail {
  /* 容器仅提供布局，段落样式由 ParagraphComponent 负责 */
}
</style>
