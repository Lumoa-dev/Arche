<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useMessage } from 'naive-ui'
import {
  getPostBySlugApi,
  getPostParagraphsApi,
  likePostApi,
  addFavoriteApi,
  removeFavoriteApi,
  getFavoriteStatusApi,
  getLikeStatusApi,
  type BlogPost,
  type ParagraphData
} from '@/components/logic/api'
import { useUserStore } from '@/lib/store/modules/user'
import ArPage from '@/components/ui/ArPage.vue'
import ArVBox from '@/components/ui/ArVBox.vue'
import PostTitle from '@/components/widgets/blog/PostTitle.vue'
import AuthorBar from '@/components/widgets/blog/AuthorBar.vue'
import PostIntro from '@/components/widgets/blog/PostIntro.vue'
import PostDetail from '@/components/widgets/blog/PostDetail.vue'

const route = useRoute()
const message = useMessage()
const userStore = useUserStore()

const post = ref<BlogPost | null>(null)
const paragraphs = ref<ParagraphData[]>([])
const liked = ref(false)
const favorited = ref(false)
const likeCount = ref(0)
const loading = ref(true)

const isLoggedIn = computed(() => userStore.isLoggedIn)
const isPostPublished = computed(() => post.value?.status === 'published')
const canInteract = computed(() => isLoggedIn.value && isPostPublished.value)

const fetchPost = async () => {
  loading.value = true
  try {
    const detail = await getPostBySlugApi(String(route.params.slug || ''))
    post.value = detail

    const tasks: Promise<unknown>[] = [
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

// ── 点赞 ──
const toggleLike = async () => {
  if (!post.value || !isLoggedIn.value) return
  try {
    await likePostApi(post.value.id, { silent: true })
    liked.value = !liked.value
    likeCount.value += liked.value ? 1 : -1
  } catch {
    message.error('操作失败')
  }
}

// ── 收藏 ──
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

onMounted(fetchPost)
</script>

<template>
  <ArPage
    :loading="loading && !post"
    style="
      max-width: 880px;
      margin: 0 auto;
      padding: var(--spacing-2xl) var(--spacing-md) var(--spacing-4xl);
    "
  >
    <!-- 加载失败 -->
    <template v-if="!post && !loading">
      <div
        style="
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          min-height: 50vh;
          gap: var(--spacing-sm);
          text-align: center;
        "
      >
        <div style="font-size: 36px; opacity: 0.6">⚠</div>
        <p
          style="
            font-size: 16px;
            font-weight: var(--font-weight-semibold);
            color: var(--text-primary);
            margin: 0;
          "
        >
          帖子加载失败
        </p>
        <p style="font-size: 13px; color: var(--text-tertiary); margin: 0">
          请检查网络连接或确认帖子是否存在
        </p>
        <button
          style="
            margin-top: var(--spacing-md);
            padding: 8px 20px;
            border: 1px solid var(--border-color);
            border-radius: var(--radius-md);
            background: var(--surface-color);
            color: var(--text-primary);
            font-size: 13px;
            font-family: var(--font-sans);
            cursor: pointer;
          "
          @click="fetchPost"
        >
          重新加载
        </button>
      </div>
    </template>

    <!-- 内容 -->
    <ArVBox v-if="post" gap="var(--spacing-lg)">
      <!-- BLOG eyebrow -->
      <div
        style="
          font-size: 11px;
          letter-spacing: 0.15em;
          color: var(--text-tertiary);
          font-weight: var(--font-weight-medium);
          text-transform: uppercase;
          display: flex;
          align-items: center;
          gap: var(--spacing-sm);
        "
      >
        BLOG
        <span
          v-if="!isPostPublished"
          style="
            display: inline-flex;
            align-items: center;
            padding: 1px 8px;
            border-radius: var(--radius-full);
            font-size: 10px;
            font-weight: var(--font-weight-semibold);
            text-transform: none;
            letter-spacing: normal;
            background: rgba(212, 160, 23, 0.12);
            color: #d4a017;
          "
        >
          {{ post.status === 'pending' ? '审核中' : post.status }}
        </span>
      </div>

      <!-- 标题 -->
      <PostTitle :title="post.title" />

      <!-- 作者栏（含操作按钮） -->
      <AuthorBar
        :post-id="post.id"
        :author-username="post.author_username ?? ''"
        :created-at="post.created_at ?? ''"
        :liked="liked"
        :favorited="favorited"
        :like-count="likeCount"
        :can-interact="canInteract"
        @toggle-like="toggleLike"
        @toggle-favorite="toggleFavorite"
      />

      <!-- 引言 -->
      <PostIntro
        :abstract="post.introduction?.abstract"
        :key-points="post.introduction?.key_points"
        :reading-time="post.introduction?.reading_time"
        :difficulty-level="post.introduction?.difficulty_level"
      />

      <!-- 正文 -->
      <PostDetail :paragraphs="paragraphs" />

      <!-- 评论区（暂关闭） -->
      <div style="padding-top: var(--spacing-md)">
        <div
          style="
            display: flex;
            align-items: center;
            gap: var(--spacing-sm);
            margin-bottom: var(--spacing-md);
          "
        >
          <h3
            style="
              margin: 0;
              font-size: 16px;
              font-weight: var(--font-weight-semibold);
              color: var(--text-primary);
            "
          >
            评论
          </h3>
        </div>
        <div
          style="
            text-align: center;
            padding: var(--spacing-lg) 0;
            font-size: 13px;
            color: var(--text-tertiary);
          "
        >
          评论功能暂时关闭，后续版本恢复
        </div>
      </div>
    </ArVBox>
  </ArPage>
</template>
