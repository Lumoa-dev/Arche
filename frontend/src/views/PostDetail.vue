<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useMessage } from 'naive-ui'
import {
  getPostBySlugApi,
  getPostParagraphsApi,
  getPostCommentsApi,
  getParagraphCommentsApi,
  createPostCommentApi,
  createParagraphCommentApi,
  likePostApi,
  addFavoriteApi,
  removeFavoriteApi,
  getFavoriteStatusApi,
  getLikeStatusApi,
  type BlogPost,
  type BlogComment,
  type ParagraphData
} from '@/components/logic/api'
import { useUserStore } from '@/lib/store/modules/user'
import PostDetail from '@/components/widgets/blog/PostDetail.vue'
import AuthorBar from '@/components/widgets/blog/AuthorBar.vue'
import FloatingActions from '@/components/widgets/blog/FloatingActions.vue'
import ParagraphCommentPanel from '@/components/widgets/blog/ParagraphCommentPanel.vue'
import LikeButton from '@/components/widgets/blog/LikeButton.vue'
import FavoriteButton from '@/components/widgets/blog/FavoriteButton.vue'
import ShareButton from '@/components/widgets/blog/ShareButton.vue'
import CommentForm from '@/components/widgets/blog/CommentForm.vue'
import CommentList from '@/components/widgets/blog/CommentList.vue'

const route = useRoute()
const message = useMessage()
const userStore = useUserStore()

const post = ref<BlogPost | null>(null)
const paragraphs = ref<ParagraphData[]>([])
const comments = ref<BlogComment[]>([])
const liked = ref(false)
const favorited = ref(false)
const likeCount = ref(0)
const posting = ref(false)
const loading = ref(true)

const isLoggedIn = computed(() => userStore.isLoggedIn)
const commentsCount = computed(() => comments.value.length)
const isPostPublished = computed(() => post.value?.status === 'published')
const canInteract = computed(() => isLoggedIn.value && isPostPublished.value)

// --- 段落评论面板状态 ---
const paragraphPanel = ref({
  visible: false,
  paragraph: null as ParagraphData | null,
  comments: [] as BlogComment[],
  loading: false,
  posting: false
})

const fetchPost = async () => {
  loading.value = true
  try {
    const detail = await getPostBySlugApi(String(route.params.slug || ''))
    post.value = detail

    // 并行获取段落、评论和登录态数据
    const tasks: Promise<unknown>[] = [
      getPostCommentsApi(detail.id, { page: 1, page_size: 50 }, { silent: true }).then(
        (commentsRes) => {
          comments.value = commentsRes.list || []
        }
      ),
      getPostParagraphsApi(detail.id, { limit: 100, offset: 0 }, { silent: true }).then((data) => {
        paragraphs.value = data
      })
    ]

    if (isLoggedIn.value) {
      tasks.push(
        getFavoriteStatusApi(detail.id, {
          silent: true,
          skipAuthLogout: true
        }).then((favStatus) => {
          favorited.value = favStatus.favorited
        }),
        getLikeStatusApi(detail.id, {
          silent: true,
          skipAuthLogout: true
        })
          .then((likeStatus) => {
            liked.value = likeStatus.liked
            likeCount.value = likeStatus.count
          })
          .catch(() => {
            liked.value = false
            likeCount.value = 0
          })
      )
    }

    await Promise.all(tasks)
  } catch (err) {
    console.error('[PostDetail] 加载帖子失败:', err)
    message.error('加载帖子失败')
  } finally {
    loading.value = false
  }
}

// --- 点赞 ---
const toggleLike = async () => {
  if (!post.value || !isLoggedIn.value) return
  try {
    await likePostApi(post.value.id, { silent: true })
    liked.value = !liked.value
    likeCount.value += liked.value ? 1 : -1
    if (post.value.likes !== undefined) {
      post.value.likes += liked.value ? 1 : -1
    }
  } catch {
    message.error('操作失败')
  }
}

// --- 收藏 ---
const toggleFavorite = async () => {
  if (!post.value || !isLoggedIn.value) return
  try {
    if (favorited.value) {
      await removeFavoriteApi(post.value.id, { silent: true })
      favorited.value = false
      message.success('已取消收藏')
    } else {
      await addFavoriteApi(post.value.id, { silent: true })
      favorited.value = true
      message.success('已收藏')
    }
  } catch {
    message.error('操作失败')
  }
}

// --- 分享 ---
const handleShare = () => {
  const url = window.location.href
  navigator.clipboard
    .writeText(url)
    .then(() => {
      message.success('链接已复制到剪贴板')
    })
    .catch(() => {
      message.error('复制失败')
    })
}

// --- 全局评论 ---
const submitComment = async (content: string) => {
  if (!post.value) return
  posting.value = true
  try {
    await createPostCommentApi(post.value.id, { content }, { silent: true })
    message.success('评论成功')
    const res = await getPostCommentsApi(
      post.value.id,
      { page: 1, page_size: 50 },
      { silent: true }
    )
    comments.value = res.list || []
  } catch {
    message.error('评论失败')
  } finally {
    posting.value = false
  }
}

// --- 段落评论 ---
const openParagraphComment = async (paragraph: ParagraphData) => {
  if (!post.value) return

  paragraphPanel.value.visible = false
  paragraphPanel.value.paragraph = paragraph
  paragraphPanel.value.comments = []
  paragraphPanel.value.loading = true

  try {
    const res = await getParagraphCommentsApi(
      post.value.id,
      paragraph.pid,
      { page: 1, page_size: 50 },
      { silent: true }
    )
    paragraphPanel.value.comments = res.list || []
  } catch {
    // 静默
  } finally {
    paragraphPanel.value.loading = false
    paragraphPanel.value.visible = true
  }
}

const submitParagraphComment = async (content: string) => {
  if (!post.value || !paragraphPanel.value.paragraph) return
  paragraphPanel.value.posting = true
  try {
    await createParagraphCommentApi(
      post.value.id,
      paragraphPanel.value.paragraph.pid,
      { content },
      { silent: true }
    )
    message.success('评论成功')
    // 重新加载段落评论
    const res = await getParagraphCommentsApi(
      post.value.id,
      paragraphPanel.value.paragraph.pid,
      { page: 1, page_size: 50 },
      { silent: true }
    )
    paragraphPanel.value.comments = res.list || []
  } catch {
    message.error('评论失败')
  } finally {
    paragraphPanel.value.posting = false
  }
}

const closeParagraphPanel = () => {
  paragraphPanel.value.visible = false
}

onMounted(fetchPost)
</script>

<template>
  <div class="post-detail-view">
    <!-- 加载态 -->
    <div v-if="loading" class="loading-state">
      <div class="ink-loading" />
      <p class="loading-text">加载中……</p>
    </div>

    <!-- 加载失败 -->
    <div v-else-if="!post" class="error-state">
      <div class="error-icon">⚠</div>
      <p class="error-text">帖子加载失败</p>
      <p class="error-hint">请检查网络连接或确认帖子是否存在</p>
      <button class="error-retry-btn" @click="fetchPost">重新加载</button>
    </div>

    <!-- 内容 -->
    <div v-else class="post-detail-page">
      <!-- BLOG eybrow + 状态 -->
      <div class="page-eyebrow">
        BLOG
        <span v-if="!isPostPublished" class="status-badge" :class="`status-${post.status}`">
          {{ post.status === 'pending' ? '审核中' : post.status }}
        </span>
      </div>

      <!-- 文章标题 -->
      <h1 class="page-title">{{ post.title }}</h1>

      <!-- 分隔线 -->
      <div class="title-divider" />

      <!-- 引言区域（结构化） -->
      <div v-if="post.introduction?.abstract" class="intro-section">
        <p class="intro-abstract">{{ post.introduction.abstract }}</p>
        <div v-if="post.introduction.key_points?.length" class="intro-key-points">
          <span v-for="point in post.introduction.key_points" :key="point" class="key-point">{{
            point
          }}</span>
        </div>
        <div v-if="post.introduction.reading_time" class="intro-meta">
          <span class="intro-reading-time">{{ post.introduction.reading_time }} 分钟阅读</span>
          <span v-if="post.introduction.difficulty_level" class="intro-difficulty">{{
            post.introduction.difficulty_level
          }}</span>
        </div>
      </div>

      <!-- 作者信息行 -->
      <AuthorBar :post-id="post.id" :author-username="post.author_username ?? ''" />

      <!-- 正文区域（含左侧浮动操作栏） -->
      <div class="content-wrapper">
        <FloatingActions
          :liked="liked"
          :favorited="favorited"
          :like-count="likeCount"
          :disabled="!canInteract"
          @toggle-like="toggleLike"
          @toggle-favorite="toggleFavorite"
          @share="handleShare"
        />

        <div class="content-main">
          <PostDetail :paragraphs="paragraphs" @paragraph-click="openParagraphComment" />
        </div>
      </div>

      <!-- 正文底部操作栏 -->
      <div class="bottom-actions">
        <LikeButton
          :count="likeCount"
          :active="liked"
          :disabled="!canInteract"
          @toggle="toggleLike"
        />
        <FavoriteButton :active="favorited" :disabled="!canInteract" @toggle="toggleFavorite" />
        <ShareButton :disabled="!isPostPublished" />
      </div>

      <!-- 全局评论区 -->
      <div class="global-comments">
        <div class="comments-header">
          <h3 class="comments-title">评论</h3>
          <span v-if="commentsCount > 0" class="comments-badge">{{ commentsCount }}</span>
        </div>

        <CommentForm v-if="isLoggedIn" :loading="posting" @submit="submitComment" />
        <div v-else class="login-hint">
          <span class="login-hint-icon">⟡</span>
          登录后即可发表评论
        </div>

        <div class="comments-divider" />

        <CommentList :comments="comments" />
      </div>
    </div>

    <!-- 段落评论浮窗 -->
    <ParagraphCommentPanel
      :visible="paragraphPanel.visible"
      :paragraph="paragraphPanel.paragraph"
      :comments="paragraphPanel.comments"
      :loading="paragraphPanel.loading"
      :posting="paragraphPanel.posting"
      :is-logged-in="isLoggedIn"
      @close="closeParagraphPanel"
      @submit-comment="submitParagraphComment"
    />
  </div>
</template>

<style scoped>
/* ── 页面布局 ── */
.post-detail-page {
  max-width: 880px;
  margin: 0 auto;
  padding: var(--spacing-2xl) var(--spacing-md) var(--spacing-4xl);
}

/* ── BLOG eybrow ── */
.page-eyebrow {
  font-size: 11px;
  letter-spacing: 0.15em;
  color: var(--text-tertiary);
  margin-bottom: var(--spacing-sm);
  font-weight: var(--font-weight-medium);
  text-transform: uppercase;
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.status-badge {
  display: inline-flex;
  align-items: center;
  padding: 1px 8px;
  border-radius: var(--radius-full);
  font-size: 10px;
  font-weight: var(--font-weight-semibold);
  text-transform: none;
  letter-spacing: normal;
}

.status-badge.status-pending {
  background: var(--warning-light-color, rgba(212, 160, 23, 0.12));
  color: var(--accent-yellow, #d4a017);
}

/* ── 标题 ── */
.page-title {
  margin: 0 0 var(--spacing-md);
  font-size: 28px;
  font-weight: var(--font-weight-bold);
  line-height: 1.35;
  color: var(--text-primary);
  letter-spacing: -0.02em;
}

/* ── 分隔线 ── */
.title-divider {
  height: 1px;
  margin: 0 0 var(--spacing-sm);
  background: linear-gradient(
    90deg,
    var(--primary-color) 0%,
    var(--divider-color) 30%,
    transparent 100%
  );
  opacity: 0.5;
}

/* ── 引言区域 ── */
.intro-section {
  margin: var(--spacing-md) 0 var(--spacing-lg);
  padding: var(--spacing-md);
  background: var(--surface-hover-color, rgba(128, 128, 128, 0.04));
  border-radius: var(--radius-sm);
  border-left: 3px solid var(--primary-color, #667eea);
}

.intro-abstract {
  font-size: 14px;
  line-height: 1.7;
  color: var(--text-secondary);
  margin: 0 0 var(--spacing-sm);
}

.intro-key-points {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: var(--spacing-sm);
}

.key-point {
  display: inline-flex;
  align-items: center;
  padding: 2px 10px;
  font-size: 12px;
  color: var(--primary-color);
  background: var(--primary-light-color, rgba(102, 126, 234, 0.08));
  border-radius: var(--radius-full);
  font-weight: var(--font-weight-medium);
}

.intro-meta {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  font-size: 12px;
  color: var(--text-tertiary);
}

.intro-reading-time,
.intro-difficulty {
  display: inline-flex;
  align-items: center;
}

/* ── 正文区域 ── */
.content-wrapper {
  position: relative;
  display: flow-root;
  margin-bottom: var(--spacing-lg);
}

.content-main {
  /* 给左侧浮动栏留空间 */
  min-height: 300px;
}

/* ── 底部操作栏 ── */
.bottom-actions {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-md) 0;
  border-top: 1px solid var(--divider-color);
  border-bottom: 1px solid var(--divider-color);
  margin-bottom: var(--spacing-xl);
}

/* ── 全局评论 ── */
.global-comments {
  padding-top: var(--spacing-md);
}

.comments-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-md);
}

.comments-title {
  margin: 0;
  font-size: 16px;
  font-weight: var(--font-weight-semibold);
  color: var(--text-primary);
}

.comments-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 22px;
  height: 22px;
  padding: 0 6px;
  border-radius: var(--radius-full);
  background: var(--primary-light-color);
  color: var(--primary-color);
  font-size: 12px;
  font-weight: var(--font-weight-semibold);
  font-variant-numeric: tabular-nums;
}

.comments-divider {
  height: 1px;
  margin: var(--spacing-md) 0;
  background: var(--divider-color);
}

.login-hint {
  text-align: center;
  padding: var(--spacing-lg) 0;
  font-size: 13px;
  color: var(--text-tertiary);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-sm);
}

.login-hint-icon {
  font-size: 16px;
  opacity: 0.5;
}

/* ── 加载态 ── */
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 50vh;
  gap: var(--spacing-md);
}

.loading-text {
  font-size: 14px;
  color: var(--text-tertiary);
}

/* ── 错误态 ── */
.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 50vh;
  gap: var(--spacing-sm);
  text-align: center;
}

.error-icon {
  font-size: 36px;
  margin-bottom: var(--spacing-sm);
  opacity: 0.6;
}

.error-text {
  font-size: 16px;
  font-weight: var(--font-weight-semibold);
  color: var(--text-primary);
  margin: 0;
}

.error-hint {
  font-size: 13px;
  color: var(--text-tertiary);
  margin: 0;
}

.error-retry-btn {
  margin-top: var(--spacing-md);
  padding: 8px 20px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  background: var(--surface-color);
  color: var(--text-primary);
  font-size: 13px;
  font-family: var(--font-sans);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.error-retry-btn:hover {
  background: var(--surface-hover-color);
  border-color: var(--primary-color);
  color: var(--primary-color);
}
</style>
