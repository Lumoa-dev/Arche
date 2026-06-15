<script setup lang="ts">
/**
 * PostListPanel — 帖子列表面板（浏览模式）
 *
 * 标签栏（全部/已发布/草稿）+ 帖子列表 + 悬停统计提示。
 * 统计详情弹窗已提取为 PostStatsModal。
 */
import { ref } from 'vue'
import { NIcon } from 'naive-ui'
import { EyeOutline, CreateOutline } from '@vicons/ionicons5'
import ArTag from '@/components/ui/ArTag.vue'
import PostStatsModal from './PostStatsModal.vue'
import type { BlogPost } from '@/components/logic/api'
import type { PostTab } from '@/components/logic/usePostManager'

withDefaults(
  defineProps<{
    posts: BlogPost[]
    loading?: boolean
    activeTab?: PostTab
  }>(),
  {
    loading: false,
    activeTab: 'all'
  }
)

const emit = defineEmits<{
  'update:activeTab': [tab: PostTab]
  'view-stats': [post: BlogPost]
  'edit-post': [post: BlogPost]
  'open-post': [post: BlogPost]
  'new-post': []
}>()

const statsPost = ref<BlogPost | null>(null)
const showStatsModal = ref(false)
const hoveredPost = ref<BlogPost | null>(null)

const statusMap: Record<string, { label: string; color: 'green' | 'yellow' | 'blue' | 'default' }> =
  {
    published: { label: '已发布', color: 'green' },
    pending: { label: '审核中', color: 'yellow' },
    draft: { label: '草稿', color: 'blue' }
  }

function getStatus(post: BlogPost) {
  const s = post.status || 'draft'
  return statusMap[s] || { label: s, color: 'default' as const }
}

const tabs: { key: PostTab; label: string }[] = [
  { key: 'all', label: '全部' },
  { key: 'published', label: '已发布' },
  { key: 'draft', label: '草稿' }
]

function handleViewStats(post: BlogPost) {
  if (statsPost.value?.id === post.id) {
    handleCloseStats()
    return
  }
  statsPost.value = post
  showStatsModal.value = true
  emit('view-stats', post)
}

function handleCloseStats() {
  showStatsModal.value = false
  statsPost.value = null
}

function handleOpenPost(post: BlogPost) {
  emit('open-post', post)
}

function handleEditPost(post: BlogPost) {
  emit('edit-post', post)
}
</script>

<template>
  <div class="post-section">
    <div class="tab-bar">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        class="tab-btn"
        :class="{ active: activeTab === tab.key }"
        @click="emit('update:activeTab', tab.key)"
      >
        {{ tab.label }}
      </button>
      <span class="tab-count">{{ posts.length }}</span>
    </div>

    <div class="post-list">
      <div v-if="loading" class="empty-state">加载中…</div>
      <div v-else-if="posts.length === 0" class="empty-state">
        <p v-if="activeTab === 'all'">还没有文章，开始你的第一篇创作吧</p>
        <p v-else-if="activeTab === 'published'">还没有已发布的文章</p>
        <p v-else>草稿箱是空的</p>
      </div>
      <div v-else class="post-items">
        <div v-for="post in posts" :key="post.id" class="post-row">
          <div class="post-info" @click="handleOpenPost(post)">
            <span class="post-title">{{ post.title || '无标题' }}</span>
            <div class="post-meta">
              <ArTag :color="getStatus(post).color" type="light" size="sm">
                {{ getStatus(post).label }}
              </ArTag>
              <span class="post-date">{{ post.created_at?.slice(0, 10) || '—' }}</span>
            </div>
          </div>
          <div class="post-actions">
            <div
              class="action-btn-wrap"
              @mouseenter="hoveredPost = post"
              @mouseleave="hoveredPost = null"
            >
              <button
                class="action-btn"
                title="数据"
                @click="handleViewStats(post)"
                @mouseenter="hoveredPost = post"
              >
                <NIcon size="16"><EyeOutline /></NIcon>
              </button>
              <Transition name="tip">
                <div
                  v-if="hoveredPost?.id === post.id && (!statsPost || statsPost.id !== post.id)"
                  class="stats-tip"
                  @mouseenter="hoveredPost = post"
                >
                  <div class="tip-row">
                    <span class="tip-label">阅读</span>
                    <span class="tip-value">{{ post.views || 0 }}</span>
                  </div>
                  <div class="tip-row">
                    <span class="tip-label">点赞</span>
                    <span class="tip-value">{{ post.likes || 0 }}</span>
                  </div>
                </div>
              </Transition>
            </div>
            <button class="action-btn" title="编辑" @click="handleEditPost(post)">
              <NIcon size="16"><CreateOutline /></NIcon>
            </button>
          </div>
        </div>
      </div>
    </div>

    <PostStatsModal :show="showStatsModal" :post="statsPost" @close="handleCloseStats" />
  </div>
</template>

<style scoped>
.post-section {
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  overflow: hidden;
}

.tab-bar {
  display: flex;
  align-items: center;
  gap: 2px;
  padding: var(--spacing-md) var(--spacing-lg);
  border-bottom: 1px solid var(--border-color);
  background: var(--bg-inset-color);
}

.tab-btn {
  border: 0;
  background: transparent;
  color: var(--text-tertiary);
  font-size: 13px;
  font-family: var(--font-sans);
  padding: 5px 14px;
  border-radius: var(--radius-full);
  cursor: pointer;
  transition: all var(--transition-fast);
  font-weight: var(--font-weight-medium);
}

.tab-btn:hover {
  color: var(--text-primary);
  background: var(--surface-strong-color);
}

.tab-btn.active {
  color: var(--primary-color);
  background: var(--primary-light-color);
}

.tab-count {
  margin-left: auto;
  font-size: 12px;
  color: var(--text-tertiary);
}

.post-items {
  padding: 0;
}

.post-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: var(--spacing-md) var(--spacing-lg);
  border-bottom: 1px solid var(--divider-color);
  transition: background var(--transition-fast);
}

.post-row:last-child {
  border-bottom: none;
}

.post-row:hover {
  background: var(--surface-strong-color);
}

.post-info {
  flex: 1;
  min-width: 0;
  cursor: pointer;
}

.post-title {
  display: block;
  font-size: 15px;
  font-weight: var(--font-weight-medium);
  color: var(--text-primary);
  line-height: 1.4;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.post-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 4px;
}

.post-date {
  font-size: 12px;
  color: var(--text-tertiary);
}

.post-actions {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
}

.action-btn-wrap {
  position: relative;
}

.action-btn {
  width: 32px;
  height: 32px;
  border: 0;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--text-tertiary);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--transition-fast);
}

.action-btn:hover {
  background: var(--surface-hover-color);
  color: var(--text-primary);
}

.stats-tip {
  position: absolute;
  bottom: calc(100% + 6px);
  right: 0;
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-lg);
  padding: 8px 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  white-space: nowrap;
  z-index: 50;
  min-width: 100px;
}

.tip-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  font-size: 12px;
}

.tip-label {
  color: var(--text-tertiary);
}

.tip-value {
  color: var(--text-primary);
  font-weight: var(--font-weight-semibold);
  font-variant-numeric: tabular-nums;
}

.tip-enter-active,
.tip-leave-active {
  transition: all 0.15s ease;
}

.tip-enter-from,
.tip-leave-to {
  opacity: 0;
  transform: translateY(4px);
}

.empty-state {
  text-align: center;
  padding: 48px 0;
  color: var(--text-tertiary);
  font-size: 14px;
}

.empty-state p {
  margin: 0;
}
</style>
