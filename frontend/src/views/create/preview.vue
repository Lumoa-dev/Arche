<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useMessage } from 'naive-ui'
import {
  getPostByIdApi,
  getPostParagraphsApi,
  type BlogPost,
  type ParagraphData
} from '@/lib/services/api'
import PostPreview from '@/components/widgets/blog/PostPreview.vue'
import ArPage from '@/components/ui/ArPage.vue'

const route = useRoute()
const router = useRouter()
const message = useMessage()

const post = ref<BlogPost | null>(null)
const paragraphs = ref<ParagraphData[]>([])
const loading = ref(true)

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

onMounted(fetchPreview)
</script>

<template>
  <ArPage
    :loading="loading"
    style="max-width: 880px; margin: 0 auto; padding: var(--spacing-2xl) var(--spacing-md)"
  >
    <PostPreview
      v-if="post"
      :post="post"
      :paragraphs="paragraphs"
      :post-id="String(route.query.postId)"
    />
  </ArPage>
</template>
