<script setup lang="ts">
import { ref, h, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useMessage } from 'naive-ui'
import { AddOutline } from '@/icons'
import { ArTable, ArPagination } from '@/components/ui'
import ArButton from '@/components/ui/ArButton.vue'
import ArTag from '@/components/ui/ArTag.vue'
import { PostCard } from '@/components/blog'
import { deletePostApi, getMyPostsApi, type BlogPost } from '@/components/logic/api'

const message = useMessage()
const router = useRouter()
const tableData = ref<PostRow[]>([])

const currentPage = ref(1)
const pageSize = ref(10)
const total = ref(0)
const loading = ref(false)

interface PostRow {
  key: string
  id: string
  title: string
  createdAt: string
  status: string
}

const toBlogPost = (row: PostRow): BlogPost => ({
  id: row.id,
  slug: row.id,
  title: row.title,
  content: '',
  tags: [],
  created_at: row.createdAt,
  status: row.status
})

const statusColorMap: Record<
  string,
  { label: string; color: 'green' | 'yellow' | 'red' | 'default' }
> = {
  published: { label: '已发布', color: 'green' },
  pending: { label: '待审核', color: 'yellow' },
  rejected: { label: '已驳回', color: 'red' }
}

const getStatusMeta = (status: string) => {
  return statusColorMap[status] || { label: status, color: 'default' as const }
}

const columns = [
  {
    title: '标题',
    key: 'title',
    width: 400,
    render: (row: PostRow) =>
      h('div', { class: 'posts-title-cell' }, [
        h(PostCard, {
          post: toBlogPost(row),
          layout: 'compact',
          showExcerpt: false
        })
      ])
  },
  {
    title: '发布时间',
    key: 'createdAt',
    width: 160
  },
  {
    title: '状态',
    key: 'status',
    width: 120,
    render: (row: { status: string }) => {
      const meta = getStatusMeta(row.status)
      return h(
        ArTag,
        { color: meta.color, type: 'light', size: 'sm' },
        { default: () => meta.label }
      )
    }
  },
  {
    title: '操作',
    key: 'actions',
    width: 180,
    render: (row: PostRow) => {
      return h('div', { style: { display: 'flex', gap: '8px' } }, [
        h(
          ArButton,
          {
            size: 'sm',
            type: 'ghost',
            onClick: () => handleEdit(row)
          },
          { default: () => '编辑' }
        ),
        h(
          ArButton,
          {
            size: 'sm',
            type: 'danger',
            onClick: () => confirmDelete(row)
          },
          { default: () => '删除' }
        )
      ])
    }
  }
]

const toPostRow = (item: BlogPost): PostRow => ({
  key: item.id,
  id: item.id,
  title: item.title,
  createdAt: item.created_at ? item.created_at.slice(0, 10) : '-',
  status: item.status || '草稿'
})

const fetchPosts = async () => {
  loading.value = true
  try {
    const res = await getMyPostsApi({
      page: currentPage.value,
      page_size: pageSize.value
    })
    const list = (res.list || []).map(toPostRow)
    tableData.value = list
    total.value = res.total
  } finally {
    loading.value = false
  }
}

const handleCreate = () => {
  router.push('/posts/new')
}

const handleEdit = (row: PostRow) => {
  router.push(`/posts/${row.id}/edit`)
}

const confirmDelete = (row: PostRow) => {
  const confirmed = window.confirm(`确定要删除文章"${row.title}"吗？`)
  if (confirmed) {
    handleDelete(row)
  }
}

const handleDelete = async (row: PostRow) => {
  try {
    await deletePostApi(row.id)
    const index = tableData.value.findIndex((item) => item.key === row.key)
    if (index > -1) {
      tableData.value.splice(index, 1)
      total.value = Math.max(0, total.value - 1)
    }
    message.success('删除成功')
  } catch {
    message.error('删除文章失败')
  }
}

const handlePageChange = (page: number) => {
  currentPage.value = page
  fetchPosts()
}

const handlePageSizeChange = (size: number) => {
  pageSize.value = size
  currentPage.value = 1
  fetchPosts()
}

onMounted(fetchPosts)
</script>

<template>
  <div class="posts-page">
    <div class="page-heading">
      <h2>我的文章</h2>
      <ArButton type="primary" @click="handleCreate">
        <template #icon><AddOutline /></template>
        新建文章
      </ArButton>
    </div>

    <div class="section-card">
      <ArTable
        :columns="columns"
        :data="tableData"
        :loading="loading"
        :row-key="(row: any) => row.key"
        single-line
      />
      <div class="pager">
        <ArPagination
          :page="currentPage"
          :page-size="pageSize"
          :item-count="total"
          :page-sizes="[10, 20, 50]"
          @update:page="handlePageChange"
          @update:page-size="handlePageSizeChange"
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
.posts-page {
  max-width: 100%;
}

.page-heading {
  display: flex;
  justify-content: space-between;
  align-items: center;
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

.pager {
  display: flex;
  justify-content: center;
  padding-top: var(--spacing-md);
}

.posts-title-cell :deep(.blog-card--compact) {
  border: none;
  padding: 0;
  background: transparent;
}
</style>
