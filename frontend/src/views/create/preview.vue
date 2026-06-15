<script setup lang="ts">
/**
 * preview.vue — 文章预览页
 *
 * 只读渲染完整的文章内容：
 * - 标题 + 副标题
 * - 引言（KV 格式：有 key 显示 K: V，无 key 居中 V）
 * - 段落列表（复用 ParagraphComponent）
 */
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useMessage } from 'naive-ui'
import {
  getPostByIdApi,
  getPostParagraphsApi,
  type BlogPost,
  type ParagraphData
} from '@/lib/services/api'
import ParagraphComponent from '@/components/widgets/blog/ParagraphComponent.vue'
import ArPage from '@/components/ui/ArPage.vue'

const route = useRoute()
const router = useRouter()
const message = useMessage()

const post = ref<BlogPost | null>(null)
const paragraphs = ref<ParagraphData[]>([])
const loading = ref(true)

const subtitles = computed(() => post.value?.subtitles || [])
const introduction = computed(() => post.value?.introduction || '')

const fetchPreview = async () => {
  const postId = route.query.postId as string
  if (!postId) {
    message.error('缺少帖子 ID')
    router.push('/create')
    return
  }

  loading.value = true
  try {
    const detail = await getPostByIdApi(postId)
    post.value = detail

    const paraList = await getPostParagraphsApi(postId, { limit: 200, offset: 0 })
    paragraphs.value = paraList
  } catch {
    message.error('加载预览失败')
  } finally {
    loading.value = false
  }
}

function goBack() {
  router.push(`/create/editor?postId=${route.query.postId}`)
}

onMounted(fetchPreview)
</script>

<template>
  <ArPage
    :loading="loading"
    style="max-width: 880px; margin: 0 auto; padding: var(--spacing-2xl) var(--spacing-md)"
  >
    <template v-if="post">
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

      <!-- 引言（富文本） -->
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
    </template>
  </ArPage>
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
