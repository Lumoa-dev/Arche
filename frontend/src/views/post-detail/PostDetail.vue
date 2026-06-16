<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useMessage } from 'naive-ui'
import { useEditor, EditorContent } from '@tiptap/vue-3'
import { StarterKit } from '@tiptap/starter-kit'
import { TextAlign } from '@tiptap/extension-text-align'
import { TextStyle } from '@tiptap/extension-text-style'
import { Underline } from '@tiptap/extension-underline'
import { Image } from '@tiptap/extension-image'
import {
  getPostBySlugApi,
  likePostApi,
  addFavoriteApi,
  removeFavoriteApi,
  getFavoriteStatusApi,
  getLikeStatusApi,
  type BlogPost
} from '@/lib/services/api'
import { useUserStore } from '@/lib/store/modules/user'
import ArPage from '@/components/ui/ArPage.vue'
import ArVBox from '@/components/ui/ArVBox.vue'
import PostTitle from '@/components/widgets/blog/PostTitle.vue'
import AuthorBar from '@/components/widgets/blog/AuthorBar.vue'
import PostIntro from '@/components/widgets/blog/PostIntro.vue'

const route = useRoute()
const message = useMessage()
const userStore = useUserStore()

const post = ref<BlogPost | null>(null)
const liked = ref(false)
const favorited = ref(false)
const likeCount = ref(0)
const loading = ref(true)

const isLoggedIn = computed(() => userStore.isLoggedIn)
const isPostPublished = computed(() => post.value?.status === 'published')
const canInteract = computed(() => isLoggedIn.value && isPostPublished.value)

/** 是否有新版 content（TipTap JSON） */
const hasContent = computed(() => !!post.value?.content)

/** TipTap 只读编辑器（渲染 content 用） */
const contentEditor = ref<ReturnType<typeof useEditor> | null>(null)

const fetchPost = async () => {
  loading.value = true
  try {
    const detail = await getPostBySlugApi(String(route.params.slug || ''))
    post.value = detail

    const tasks: Promise<unknown>[] = []

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

    // 初始化 TipTap 只读编辑器（如果有新版 content）
    if (detail.content) {
      initContentEditor(detail.content)
    }
  } catch (err) {
    console.error('[PostDetail] 加载帖子失败:', err)
    message.error('加载帖子失败')
  } finally {
    loading.value = false
  }
}

function initContentEditor(contentJson: string) {
  try {
    const json = JSON.parse(contentJson)
    contentEditor.value = useEditor({
      content: json,
      editable: false,
      extensions: [
        StarterKit.configure({
          heading: { levels: [1, 2, 3, 4] }
        }),
        TextStyle,
        TextAlign.configure({ types: ['heading', 'paragraph'] }),
        Underline,
        Image.configure({ inline: false })
      ],
      editorProps: {
        attributes: {
          class: 'post-content-editor'
        }
      }
    })
  } catch {
    // 解析失败，用段落模式兜底
    contentEditor.value = null
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
      <PostIntro v-if="post.introduction" :content="post.introduction" />

      <!-- 正文：TipTap 渲染 -->
      <div v-if="hasContent && contentEditor" class="post-content-wrapper">
        <EditorContent :editor="contentEditor" />
      </div>

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

<style scoped>
.post-content-wrapper {
  font-family: var(--font-serif);
  line-height: 1.8;
  color: var(--text-primary);
}

.post-content-wrapper :deep(.ProseMirror) {
  outline: none;
}

.post-content-wrapper :deep(.ProseMirror p) {
  margin: 0.6em 0;
}

.post-content-wrapper :deep(.ProseMirror h1) {
  font-size: 1.8em;
  font-weight: var(--font-weight-bold);
  margin: 0.8em 0 0.4em;
}

.post-content-wrapper :deep(.ProseMirror h2) {
  font-size: 1.5em;
  font-weight: var(--font-weight-bold);
  margin: 0.7em 0 0.3em;
}

.post-content-wrapper :deep(.ProseMirror h3) {
  font-size: 1.25em;
  font-weight: var(--font-weight-semibold);
  margin: 0.6em 0 0.3em;
}

.post-content-wrapper :deep(.ProseMirror ul),
.post-content-wrapper :deep(.ProseMirror ol) {
  padding-left: 1.5em;
}

.post-content-wrapper :deep(.ProseMirror blockquote) {
  border-left: 3px solid var(--border-color);
  padding-left: var(--spacing-md);
  color: var(--text-secondary);
  font-style: italic;
  margin: 0.5em 0;
}

.post-content-wrapper :deep(.ProseMirror pre) {
  background: var(--surface-hover-color);
  border-radius: var(--radius-sm);
  padding: var(--spacing-md);
  font-family: var(--font-mono);
  font-size: 0.9em;
  overflow-x: auto;
}

.post-content-wrapper :deep(.ProseMirror img) {
  max-width: 100%;
  height: auto;
  border-radius: var(--radius-sm);
  margin: var(--spacing-md) 0;
}
</style>
