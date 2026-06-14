<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useMessage } from 'naive-ui'
import { PostEditor } from '@/components/blog'
import {
  createPostApi,
  updatePostApi,
  getPostByIdApi,
  type BlogPost,
  type CreatePostPayload,
  type UpdatePostPayload
} from '@/components/logic/api'
import { uploadOssFileApi } from '@/components/logic/api/oss'
import { generateTextCover } from '@/lib/utils/generateTextCover'

const route = useRoute()
const router = useRouter()
const message = useMessage()

const loading = ref(false)
const submitting = ref(false)
const post = ref<BlogPost | null>(null)

const mode = computed(() => (route.params.id ? 'edit' : 'create'))
const postId = computed(() => String(route.params.id || ''))

const fetchDetail = async () => {
  if (mode.value !== 'edit') return
  loading.value = true
  try {
    const detail = await getPostByIdApi(postId.value)
    post.value = detail
  } finally {
    loading.value = false
  }
}

const handleSave = async (payload: CreatePostPayload | UpdatePostPayload) => {
  submitting.value = true
  try {
    // 没有封面 → 自动生成文字封面并上传 OSS
    if (!payload.cover_url && payload.title) {
      const textCoverDataUrl = generateTextCover(
        {
          id: '',
          slug: '',
          title: payload.title,
          intro: (payload as any).intro || undefined,
          content: payload.content || '',
          tags: (payload as any).tags || []
        } as BlogPost,
        true
      )
      const blob = await fetch(textCoverDataUrl).then((r) => r.blob())
      const file = new File([blob], 'text-cover.jpg', { type: 'image/jpeg' })
      const resp = await uploadOssFileApi(file, false)
      const respData = resp as unknown as { data?: { id: string } }
      if (respData?.data?.id) {
        ;(payload as any).auto_cover_url = `/api/oss/files/${respData.data.id}`
      }
    }

    if (mode.value === 'edit') {
      await updatePostApi(postId.value, payload)
      message.success('保存成功')
    } else {
      await createPostApi(payload as CreatePostPayload)
      message.success('发布成功，帖子已提交审核')
    }
    await router.push('/posts')
  } catch {
    message.error(mode.value === 'edit' ? '保存失败，请重试' : '发布失败，请重试')
  } finally {
    submitting.value = false
  }
}

const handleCancel = () => {
  router.push('/posts')
}

onMounted(fetchDetail)
</script>

<template>
  <div class="page-wrapper">
    <div class="page-heading">
      <h2>{{ mode === 'edit' ? '编辑文章' : '创作新文章' }}</h2>
    </div>
    <div class="section-card">
      <PostEditor :post="post" :loading="submitting" @save="handleSave" @cancel="handleCancel" />
    </div>
  </div>
</template>

<style scoped>
.page-wrapper {
  max-width: 100%;
}

.page-heading {
  margin-bottom: var(--spacing-lg);
}

.page-heading h2 {
  margin: 0;
  font-size: 24px;
  font-weight: var(--font-weight-bold);
  color: var(--text-primary);
}

.section-card {
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: var(--spacing-lg);
  backdrop-filter: blur(4px);
}
</style>
