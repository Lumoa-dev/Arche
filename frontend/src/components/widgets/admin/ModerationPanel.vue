<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { marked } from 'marked'
import { NInput, NSelect, NEmpty, useMessage } from 'naive-ui'
import {
  getModerationPendingApi,
  approvePostApi,
  rejectPostApi,
  deletePostApi,
  type BlogPost
} from '@/components/logic/api'
import { ArButton, ArTag, ArPopconfirm } from '@/components/ui'

function renderContent(text: string): string {
  return marked.parse(text, { gfm: true }) as string
}

const message = useMessage()
const q = ref('')
const status = ref('pending')
const posts = ref<BlogPost[]>([])
const total = ref(0)
const loading = ref(false)
const selectedPost = ref<BlogPost | null>(null)
const page = ref(1)
const pageSize = 20

const statusOptions = [
  { label: '全部', value: '' },
  { label: '待审核', value: 'pending' },
  { label: '已发布', value: 'published' },
  { label: '已驳回', value: 'rejected' }
]

const statusMap: Record<string, { label: string; color: 'yellow' | 'green' | 'red' | 'default' }> =
  {
    published: { label: '已发布', color: 'green' },
    pending: { label: '待审核', color: 'yellow' },
    rejected: { label: '已驳回', color: 'red' }
  }

const fetchPosts = async (resetPage = false) => {
  if (resetPage) page.value = 1
  loading.value = true
  try {
    const params: Record<string, unknown> = { page: page.value, page_size: pageSize }
    if (q.value) params.q = q.value
    if (status.value) params.status = status.value
    const res = await getModerationPendingApi(params, { silent: true })
    posts.value = (res as unknown as { list: BlogPost[] }).list || []
    total.value = (res as unknown as { total: number }).total || 0
  } catch {
    message.error('获取帖子列表失败')
  } finally {
    loading.value = false
  }
}

const viewPost = (post: BlogPost) => {
  selectedPost.value = post
}

const doApprove = async (id: string) => {
  try {
    await approvePostApi(id, { silent: true })
    message.success('已通过')
    selectedPost.value = null
    await fetchPosts()
  } catch {
    message.error('审批失败')
  }
}

const doReject = async (id: string) => {
  try {
    await rejectPostApi(id, { silent: true })
    message.success('已驳回')
    selectedPost.value = null
    await fetchPosts()
  } catch {
    message.error('驳回失败')
  }
}

const doDelete = async (id: string) => {
  try {
    await deletePostApi(id, { silent: true })
    message.success('已删除')
    selectedPost.value = null
    await fetchPosts()
  } catch {
    message.error('删除失败')
  }
}

const statusLabel = (s: string | undefined) =>
  statusMap[s ?? ''] || { label: s ?? '未知', color: 'default' as const }

onMounted(() => fetchPosts())
</script>

<template>
  <div class="moderation-panel">
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

    <div class="split-layout">
      <div class="list-panel">
        <div v-if="loading && posts.length === 0" class="empty-state">
          <NEmpty description="加载中..." />
        </div>
        <div v-else-if="posts.length === 0" class="empty-state">
          <NEmpty description="暂无帖子" />
        </div>
        <div v-else class="post-cards">
          <div
            v-for="post in posts"
            :key="post.id"
            class="post-card"
            :class="{ active: selectedPost?.id === post.id }"
            @click="viewPost(post)"
          >
            <div class="card-header">
              <span class="card-title">{{ post.title }}</span>
              <ArTag :color="statusLabel(post.status).color" size="sm">
                {{ statusLabel(post.status).label }}
              </ArTag>
            </div>
            <div class="card-meta">
              <span>{{ post.author_username || '匿名' }}</span>
              <span>{{ post.created_at?.slice(0, 10) }}</span>
            </div>
          </div>
        </div>
      </div>

      <div class="detail-panel">
        <template v-if="selectedPost">
          <div class="detail-header">
            <h3>{{ selectedPost.title }}</h3>
            <div class="detail-actions">
              <ArButton type="primary" size="sm" @click="doApprove(selectedPost.id)">
                通过
              </ArButton>
              <ArButton type="ghost" size="sm" @click="doReject(selectedPost.id)"> 驳回 </ArButton>
              <ArPopconfirm
                title="确认删除"
                :content="`确定删除「${selectedPost.title}」？`"
                positive-text="确认"
                negative-text="取消"
                @positive-click="doDelete(selectedPost.id)"
              >
                <template #trigger>
                  <ArButton type="danger" size="sm">删除</ArButton>
                </template>
              </ArPopconfirm>
            </div>
          </div>
          <div class="detail-meta">
            <span>作者：{{ selectedPost.author_username || '匿名' }}</span>
            <span>
              状态：
              <ArTag :color="statusLabel(selectedPost.status).color" size="sm">
                {{ statusLabel(selectedPost.status).label }}
              </ArTag>
            </span>
            <span>创建：{{ selectedPost.created_at?.slice(0, 10) }}</span>
          </div>
          <!-- eslint-disable-next-line vue/no-v-html -->
          <div class="detail-content" v-html="renderContent(selectedPost.content || '')" />
        </template>
        <template v-else>
          <div class="empty-state">
            <NEmpty description="点击左侧帖子查看详情" />
          </div>
        </template>
      </div>
    </div>
  </div>
</template>

<style scoped>
.moderation-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
  height: 100%;
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

.split-layout {
  display: flex;
  gap: 12px;
  flex: 1;
  min-height: 0;
}

.list-panel {
  width: 380px;
  flex-shrink: 0;
  overflow-y: auto;
  background: var(--surface-color);
  border: var(--glass-border);
  border-radius: var(--radius-md);
  padding: 8px;
}

.detail-panel {
  flex: 1;
  overflow-y: auto;
  background: var(--surface-color);
  border: var(--glass-border);
  border-radius: var(--radius-md);
  padding: 20px;
}

.empty-state {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 200px;
}

.post-cards {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.post-card {
  padding: 10px 12px;
  border-radius: 6px;
  cursor: pointer;
  border: 1px solid transparent;
  transition: all 0.15s;
}

.post-card:hover {
  background: var(--glass-bg-hover);
  border-color: var(--border-color);
}

.post-card.active {
  background: var(--primary-light-color);
  border-color: color-mix(in srgb, var(--primary-color) 30%, transparent);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 8px;
  margin-bottom: 4px;
}

.card-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
}

.card-meta {
  display: flex;
  gap: 12px;
  font-size: 12px;
  color: var(--text-tertiary);
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 12px;
}

.detail-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
  color: var(--text-primary);
}

.detail-actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

.detail-meta {
  display: flex;
  gap: 16px;
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 16px;
  align-items: center;
}

.detail-content {
  font-size: 14px;
  line-height: 1.7;
  color: var(--text-primary);
  white-space: pre-wrap;
}
</style>
