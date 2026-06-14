<script setup lang="ts">
import { computed } from 'vue'
import ParagraphComponent from './ParagraphComponent.vue'
import type { ParagraphData } from '@/components/logic/api'

const props = defineProps<{
  paragraphs: ParagraphData[]
}>()

const emit = defineEmits<{
  paragraphClick: [paragraph: ParagraphData]
}>()

const enrichedParagraphs = computed(() => {
  return props.paragraphs.map((para, index) => ({
    ...para,
    displayIndex: index + 1
  }))
})

function handleParagraphClick(para: ParagraphData) {
  emit('paragraphClick', para)
}
</script>

<template>
  <article class="post-detail">
    <ParagraphComponent
      v-for="para in enrichedParagraphs"
      :key="para.pid"
      :paragraph="para"
      :index="para.displayIndex"
      @click="handleParagraphClick"
    />
  </article>
</template>

<style scoped>
.post-detail {
  /* 容器仅提供布局，段落样式由 ParagraphComponent 负责 */
}
</style>
