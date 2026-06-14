<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { getMyPostsApi, getPostCommentsApi, type BlogPost } from '@/components/logic/api'
import ArTable from '@/components/ui/ArTable.vue'
import type { ArTableColumn } from '@/components/ui/ArTable.vue'

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
  <div class="creator-dashboard">
    <div class="page-heading">
      <h2>创作者看板</h2>
    </div>

    <div class="alert-note">
      TODO：后端补充 analytics 接口后，将聚合逻辑替换为 /blog/analytics/*。
    </div>

    <div class="stats-grid">
      <div v-for="card in statCards" :key="card.label" class="section-card stat-card">
        <div class="stat-label">{{ card.label }}</div>
        <div class="stat-value">{{ card.value }}</div>
      </div>
    </div>

    <div class="section-card table-card">
      <div class="card-header">
        <span class="card-header-title">内容表现排行（近 50 篇）</span>
      </div>
      <div class="table-wrap" :class="{ 'is-loading': loading }">
        <ArTable :columns="columns" :data="rows" :loading="loading" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.creator-dashboard {
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

.alert-note {
  margin-bottom: var(--spacing-md);
  padding: var(--spacing-sm) var(--spacing-md);
  background: var(--primary-light-color);
  border-left: 3px solid var(--primary-color);
  border-radius: var(--radius-sm);
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.5;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-bottom: var(--spacing-md);
}

.section-card {
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  backdrop-filter: blur(4px);
}

.stat-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: var(--spacing-lg);
}

.stat-label {
  color: var(--text-secondary);
  margin-bottom: 6px;
  font-size: 14px;
}

.stat-value {
  font-size: 28px;
  font-weight: var(--font-weight-bold);
  color: var(--text-primary);
}

.table-card {
  margin-top: var(--spacing-md);
  padding: var(--spacing-lg);
}

.card-header {
  margin-bottom: var(--spacing-md);
}

.card-header-title {
  font-size: 16px;
  font-weight: var(--font-weight-semibold);
  color: var(--text-primary);
}

.table-wrap {
  min-height: 100px;
}

.table-wrap.is-loading {
  opacity: 0.6;
  pointer-events: none;
}
</style>
