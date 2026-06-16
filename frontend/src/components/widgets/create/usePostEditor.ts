/**
 * usePostEditor — 编辑器的核心数据管理
 *
 * 负责帖子的加载/保存、标题/副标题/正文管理。
 * 正文以 TipTap JSON 字符串形式存储在后端 BlogPost.content 字段。
 */
import { ref, computed } from 'vue'
import { useMessage } from 'naive-ui'
import {
  getPostByIdApi,
  createPostApi,
  updatePostApi,
  type CreatePostPayload
} from '@/lib/services/api'

/** 编辑器完整状态 */
export interface EditorState {
  postId: string | null
  title: string
  subtitles: string[]
  coverUrl: string
  tags: string[]
  requiredLevel: number
}

export function usePostEditor() {
  const message = useMessage()

  // ── 状态 ──
  const postId = ref<string | null>(null)
  const title = ref('')
  const subtitles = ref<string[]>([])
  const coverUrl = ref('')
  const tags = ref<string[]>([])
  const requiredLevel = ref(5)
  const loading = ref(false)
  const saving = ref(false)

  /** TipTap 编辑器内容（JSON 字符串，由 editor.vue 维护） */
  const content = ref<string>('')

  /** 是否编辑中（vs 新建） */
  const isEdit = computed(() => postId.value !== null)

  // ── 加载与保存 ──

  /** 加载帖子到编辑器 */
  async function loadPost(id: string) {
    loading.value = true
    try {
      const post = await getPostByIdApi(id)
      postId.value = post.id
      title.value = post.title || ''
      subtitles.value = post.subtitles || []
      coverUrl.value = post.cover_url || ''
      tags.value = post.tags || []
      requiredLevel.value = post.required_level ?? 5
      content.value = post.content || ''
    } catch {
      message.error('加载帖子失败')
    } finally {
      loading.value = false
    }
  }

  /** 重置编辑器（新建时调用） */
  function resetForNew() {
    postId.value = null
    title.value = ''
    subtitles.value = []
    coverUrl.value = ''
    tags.value = []
    requiredLevel.value = 5
    content.value = ''
  }

  /** 保存帖子 */
  async function save() {
    if (!title.value.trim()) {
      message.warning('标题不能为空')
      return false
    }

    saving.value = true
    try {
      const payload: CreatePostPayload = {
        title: title.value.trim(),
        subtitles: subtitles.value.filter((s) => s.trim()),
        tags: tags.value,
        required_level: requiredLevel.value,
        ...(coverUrl.value ? { cover_url: coverUrl.value } : {}),
        ...(content.value ? { content: content.value } : {})
      }

      if (isEdit.value) {
        await updatePostApi(postId.value!, payload)
        message.success('保存成功')
      } else {
        const display = await createPostApi(payload as CreatePostPayload)
        postId.value = display.id
        message.success('发布成功，帖子已提交审核')
      }

      return true
    } catch (e) {
      const msg = (e as Error).message || '保存失败，请重试'
      message.error(msg)
      return false
    } finally {
      saving.value = false
    }
  }

  return {
    // 状态
    postId,
    title,
    subtitles,
    content,
    coverUrl,
    tags,
    requiredLevel,
    loading,
    saving,
    isEdit,

    // 生命周期
    loadPost,
    resetForNew,
    save
  }
}
