<template>
  <ArVBox gap="var(--spacing-lg)">
    <ArPageHeader title="创作" desc="写文章、管理内容，记录你的所思所想">
      <ArButton type="primary" size="lg" @click="router.push('/create/editor')">
        <template #icon
          ><NIcon size="18"><CreateOutline /></NIcon
        ></template>
        写文章
      </ArButton>
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
  </ArVBox>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { NIcon } from 'naive-ui'
import { CreateOutline } from '@vicons/ionicons5'
import ArVBox from '@/components/ui/ArVBox.vue'
import ArButton from '@/components/ui/ArButton.vue'
import ArPageHeader from '@/components/ui/ArPageHeader.vue'
import PostStatsCards from '@/components/widgets/create/PostStatsCards.vue'
import PostListPanel from '@/components/widgets/create/PostListPanel.vue'
import { usePostManager } from '@/components/widgets/create/usePostManager'
import type { BlogPost } from '@/lib/services/api'

const router = useRouter()
const manager = usePostManager()

function handleOpenPost(post: BlogPost) {
  router.push(`/blog/${post.slug}`)
}

function handleEditPost(post: BlogPost) {
  router.push(`/create/editor?postId=${post.id}`)
}

onMounted(() => {
  manager.fetchData()
})
</script>
