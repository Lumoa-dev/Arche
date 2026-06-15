<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import ParagraphComponent from '@/components/widgets/blog/ParagraphComponent.vue'
import type { BlogPost, ParagraphData } from '@/lib/services/api'

const props = defineProps<{
  post: BlogPost
  paragraphs: ParagraphData[]
  postId: string
}>()

const router = useRouter()
const subtitles = computed(() => props.post?.subtitles || [])
const introduction = computed(() => props.post?.introduction || '')

function goBack() {
  router.push(`/create/editor?postId=${props.postId}`)
}
</script>

<template>
  <div>
    <!-- 返回编辑 -->
    <div style="margin-bottom: var(--spacing-lg)">
      <button class="back-btn" @click="goBack">← 返回编辑</button>
    </div>

    <!-- 标题 -->
    <h1 class="preview-title">{{ post.title }}</h1>

    <!-- 副标题 -->
    <div v-if="subtitles.length > 0" class="preview-subtitles">
      <p v-for="(sub, idx) in subtitles" :key="idx" class="preview-subtitle">
        {{ sub }}
      </p>
    </div>

    <!-- 引言 -->
    <!-- eslint-disable-next-line vue/no-v-html -->
    <div v-if="introduction" class="preview-introduction" v-html="introduction" />

    <!-- 段落 -->
    <article class="preview-paragraphs">
      <ParagraphComponent
        v-for="(para, idx) in paragraphs"
        :key="para.pid"
        :paragraph="para"
        :index="idx + 1"
      />
    </article>
  </div>
</template>

<style scoped>
.back-btn {
  padding: 6px 16px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  background: var(--surface-color);
  color: var(--text-secondary);
  font-size: 13px;
  font-family: var(--font-sans);
  cursor: pointer;
  transition: all var(--transition-fast);
}
.back-btn:hover {
  border-color: var(--primary-color);
  color: var(--primary-color);
}
.preview-title {
  font-size: 2em;
  font-weight: var(--font-weight-bold);
  line-height: 1.3;
  margin: 0 0 var(--spacing-sm);
  color: var(--text-primary);
  font-family: var(--font-serif);
}
.preview-subtitles {
  margin-bottom: var(--spacing-lg);
}
.preview-subtitle {
  font-size: 1.1em;
  color: var(--text-tertiary);
  margin: 0.2em 0;
  line-height: 1.5;
  font-family: var(--font-serif);
}
.preview-introduction {
  margin: var(--spacing-md) 0 var(--spacing-lg);
  padding: var(--spacing-md);
  background: var(--surface-hover-color);
  border-radius: var(--radius-sm);
  border-left: 3px solid var(--primary-color);
  font-family: var(--font-serif);
  font-size: 1.05em;
  line-height: 1.7;
  color: var(--text-secondary);
}
.preview-paragraphs {
  margin-top: var(--spacing-lg);
}
</style>
