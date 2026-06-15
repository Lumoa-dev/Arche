<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { getMyPostsApi, getPostCommentsApi, type BlogPost } from '@/lib/services/api'
import ArTable from '@/components/ui/ArTable.vue'
import ArCard from '@/components/ui/ArCard.vue'
import ArGrid from '@/components/ui/ArGrid.vue'
import type { ArTableColumn } from '@/components/ui/ArTable.vue'
import PageHeading from '@/components/widgets/common/PageHeading.vue'
import StatCard from '@/components/widgets/admin/StatCard.vue'
import AlertNote from '@/components/widgets/common/AlertNote.vue'

interface MetricRow {
  key: string
  title: string
  status: string
  comments: number
  likes: number
  createdAt: string
}

const loading = ref(false)
const rows = ref<MetricRow[]>([])
const totalPosts = ref(0)
const totalComments = ref(0)
const totalLikes = ref(0)

const columns: ArTableColumn[] = [
  { title: '标题', key: 'title' },
  { title: '状态', key: 'status' },
  {
    title: '评论数',
    key: 'comments',
    sortable: true,
    sorter: (a: MetricRow, b: MetricRow) => a.comments - b.comments
  },
  {
    title: '点赞',
    key: 'likes',
    sortable: true,
    sorter: (a: MetricRow, b: MetricRow) => a.likes - b.likes
  },
  { title: '创建时间', key: 'createdAt' }
]

const statCards = computed(() => [
  { label: '文章总数', value: totalPosts.value },
  { label: '总评论', value: totalComments.value },
  { label: '总点赞', value: totalLikes.value }
])

const fetchData = async () => {
  loading.value = true
  try {
    const res = await getMyPostsApi(
      { page: 1, page_size: 50 },
      { silent: true, skipAuthLogout: true }
    )
    const list = res.list || []
    totalPosts.value = list.length

    const commentTotals = await Promise.all(
      list.map(async (post: BlogPost) => {
        const comments = await getPostCommentsApi(
          post.id,
          { page: 1, page_size: 1 },
          { silent: true, skipAuthLogout: true }
        )
        return {
          post,
          comments: comments.total || 0
        }
      })
    )

    rows.value = commentTotals.map(({ post, comments }) => ({
      key: post.id,
      title: post.title,
      status: post.status ?? 'pending',
      comments,
      likes: post.likes || 0,
      createdAt: post.created_at?.slice(0, 10) || '-'
    }))

    totalComments.value = rows.value.reduce((sum, item) => sum + item.comments, 0)
    totalLikes.value = rows.value.reduce((sum, item) => sum + item.likes, 0)
  } catch {
    rows.value = []
    totalPosts.value = 0
    totalComments.value = 0
    totalLikes.value = 0
  } finally {
    loading.value = false
  }
}

onMounted(fetchData)
</script>

<template>
  <div>
    <PageHeading title="创作者看板" />

    <AlertNote>
      TODO：后端补充 analytics 接口后，将聚合逻辑替换为 /blog/analytics/*。
    </AlertNote>

    <ArGrid :cols="3" gap="12px" style="margin-bottom: var(--spacing-md);">
      <StatCard v-for="card in statCards" :key="card.label" :label="card.label" :value="card.value" />
    </ArGrid>

    <ArCard variant="elevated" padding="lg">
      <div style="margin-bottom: var(--spacing-md);">
        <span style="font-size: 16px; font-weight: var(--font-weight-semibold); color: var(--text-primary);">内容表现排行（近 50 篇）</span>
      </div>
      <ArTable :columns="columns" :data="rows" :loading="loading" />
    </ArCard>
  </div>
</template>
