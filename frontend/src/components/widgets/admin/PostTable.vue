<script setup lang="ts">
import { h, ref } from 'vue'
import { NInput, NSelect, NPopconfirm, useMessage } from 'naive-ui'
import type { ArTableColumn } from '@/components/ui/ArTable.vue'
import { getBlogPostsApi, deletePostApi, type BlogPost } from '@/components/logic/api'
import { ArButton, ArTag, ArTable, ArPagination } from '@/components/ui'

interface PostRow {
  key: string
  id: string
  title: string
  author: string
  status: string
  createdAt: string
}

const message = useMessage()
const q = ref('')
const status = ref('')
const posts = ref<PostRow[]>([])
const total = ref(0)
const loading = ref(false)
const page = ref(1)
let pageSize: number = 10

const statusOptions = [
  { label: '全部状态', value: '' },
  { label: '待审核', value: 'pending' },
  { label: '已发布', value: 'published' },
  { label: '已驳回', value: 'rejected' }
]

const statusTagMap: Record<
  string,
  { label: string; color: 'green' | 'yellow' | 'red' | 'default' }
> = {
  published: { label: '已发布', color: 'green' },
  pending: { label: '待审核', color: 'yellow' },
  rejected: { label: '已驳回', color: 'red' }
}

const columns: ArTableColumn[] = [
  {
    title: '标题',
    key: 'title',
    ellipsis: true
  },
  {
    title: '作者',
    key: 'author',
    width: 140
  },
  {
    title: '状态',
    key: 'status',
    width: 100,
    render: (row: PostRow) => {
      const tag = statusTagMap[row.status] || {
        label: row.status || '未知',
        color: 'default' as const
      }
      return h(ArTag, { color: tag.color, size: 'sm' }, { default: () => tag.label })
    }
  },
  {
    title: '创建时间',
    key: 'createdAt',
    width: 120
  },
  {
    title: '操作',
    key: 'actions',
    width: 160,
    render: (row: PostRow) => {
      return h('div', { class: 'action-cell' }, [
        h(
          ArButton,
          {
            type: 'ghost',
            size: 'sm',
            onClick: () => handleEdit(row)
          },
          { default: () => '编辑' }
        ),
        h(
          NPopconfirm,
          {
            title: '确认删除',
            content: `确定删除「${row.title}」？`,
            positiveText: '确认',
            negativeText: '取消',
            onPositiveClick: () => handleDelete(row)
          },
          {
            trigger: () => h(ArButton, { type: 'danger', size: 'sm' }, { default: () => '删除' })
          }
        )
      ])
    }
  }
]

const fetchPosts = async (resetPage = false) => {
  if (resetPage) page.value = 1
  loading.value = true
  try {
    const params: Record<string, unknown> = { page: page.value, page_size: pageSize }
    if (q.value) params.q = q.value
    if (status.value) params.status = status.value
    const res = await getBlogPostsApi(params, { silent: true })
    const list = (res as unknown as { list: BlogPost[] }).list || []
    posts.value = list.map((item) => ({
      key: item.id,
      id: item.id,
      title: item.title,
      author: item.author_username || '匿名',
      status: item.status || '',
      createdAt: item.created_at ? item.created_at.slice(0, 10) : '-'
    }))
    total.value = (res as unknown as { total: number }).total || 0
  } catch {
    message.error('获取帖子列表失败')
  } finally {
    loading.value = false
  }
}

const handleEdit = (row: PostRow) => {
  message.info(`编辑：${row.title}`)
}

const handleDelete = async (row: PostRow) => {
  try {
    await deletePostApi(row.id, { silent: true })
    message.success('已删除')
    await fetchPosts()
  } catch {
    message.error('删除失败')
  }
}

const handlePageChange = (p: number) => {
  page.value = p
  fetchPosts()
}
</script>

<template>
  <div class="post-table">
    <div class="toolbar">
      <div class="toolbar-left">
        <NInput
          v-model:value="q"
          placeholder="搜索标题..."
          clearable
          size="small"
          style="width: 240px"
          @keyup.enter="fetchPosts(true)"
        />
        <NSelect
          v-model:value="status"
          :options="statusOptions"
          size="small"
          style="width: 120px"
          @update:value="fetchPosts(true)"
        />
      </div>
      <div class="toolbar-right">
        <ArButton size="sm" @click="fetchPosts()">刷新</ArButton>
      </div>
    </div>

    <div class="table-wrapper">
      <ArTable
        :columns="columns"
        :data="posts"
        :loading="loading"
        :bordered="false"
        :single-line="true"
        size="small"
        striped
      />
    </div>

    <div class="pager">
      <ArPagination
        :page="page"
        :page-size="pageSize"
        :item-count="total"
        :page-sizes="[10, 20, 50]"
        @update:page="handlePageChange"
        @update:page-size="
          (v: number) => {
            pageSize = v
            page = 1
            fetchPosts(true)
          }
        "
      />
    </div>
  </div>
</template>

<style scoped>
.post-table {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.toolbar-left {
  display: flex;
  gap: 8px;
  align-items: center;
}

.toolbar-right {
  display: flex;
  gap: 8px;
}

.table-wrapper {
  background: var(--surface-color);
  border: var(--glass-border);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.pager {
  display: flex;
  justify-content: center;
  padding-top: 4px;
}

.action-cell {
  display: flex;
  gap: 8px;
  align-items: center;
}
</style>
