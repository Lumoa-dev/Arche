<template>
  <div class="create-page">
    <ArPageHeader title="创作" desc="写文章、管理内容，记录你的所思所想">
      <ArButton type="primary" size="lg" @click="router.push('/create/editor')">
        <template #icon
          ><NIcon size="18"><CreateOutline /></NIcon
        ></template>
        写文章
      </ArButton>
      <ArButton type="secondary" size="lg" @click="handleUploadFile">
        <template #icon
          ><NIcon size="18"><CloudUploadOutline /></NIcon
        ></template>
        上传文件
      </ArButton>
      <input
        ref="fileInputRef"
        type="file"
        accept=".txt,.md"
        style="display: none"
        @change="handleFileSelected"
      />
    </ArPageHeader>
    <PostStatsCards :stat-cards="manager.statCards.value" />
    <PostListPanel
      :posts="manager.filteredPosts.value"
      :loading="manager.loading.value"
      :active-tab="manager.activeTab.value"
      @update:active-tab="manager.activeTab.value = $event"
      @edit-post="handleEditPost"
      @open-post="handleOpenPost"
      @new-post="() => router.push('/create/editor')"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { NIcon, useMessage } from 'naive-ui'
import { CreateOutline, CloudUploadOutline } from '@vicons/ionicons5'
import ArButton from '@/components/ui/ArButton.vue'
import ArPageHeader from '@/components/ui/ArPageHeader.vue'
import PostStatsCards from '@/components/widgets/blog/PostStatsCards.vue'
import PostListPanel from '@/components/widgets/blog/PostListPanel.vue'
import { usePostManager } from '@/components/logic/usePostManager'
import { uploadPostFileApi } from '@/components/logic/api'
import type { BlogPost } from '@/components/logic/api'

const router = useRouter()
const message = useMessage()
const fileInputRef = ref<HTMLInputElement | null>(null)
const manager = usePostManager()

function handleUploadFile() {
  fileInputRef.value?.click()
}

async function handleFileSelected(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  try {
    await uploadPostFileApi(file, { silent: true })
    message.success('文件导入成功')
    router.push('/create/editor')
  } catch {
    message.error('文件导入失败')
  } finally {
    input.value = ''
  }
}

function handleOpenPost(post: BlogPost) {
  router.push(`/blog/${post.slug}`)
}

function handleEditPost(post: BlogPost) {
  sessionStorage.setItem('editPostId', post.id)
  router.push('/create/editor')
}

onMounted(() => {
  manager.fetchData()
})
</script>

<style scoped>
.create-page {
  max-width: 100%;
  display: flex;
  flex-direction: column;
  gap: var(--spacing-lg);
}
</style>
