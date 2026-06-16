/**
 * useParagraphEditor — 段落编辑器的核心数据管理
 *
 * 负责帖子的加载/保存、段落增删改排序、标题/副标题/引言管理。
 * 供 EditorToolbar / EditorTitleArea / EditorParagraphCard 等组件共享状态。
 */
import { ref, computed } from 'vue'
import { useMessage } from 'naive-ui'
import {
  getPostByIdApi,
  getPostParagraphsApi,
  createPostApi,
  updatePostApi,
  type CreatePostPayload,
  type ParagraphData
} from '@/lib/services/api'
import { runPipeline, type PipelineProgress, type PipelineResult } from '@/lib/pipeline'

/** 编辑器可用的段落类型 */
export type ParagraphType = 'text' | 'heading' | 'image' | 'video' | 'code' | 'table' | 'separator'

/** 编辑器内部使用的段落数据（比后端 ParagraphData 多了临时 id 和列表状态） */
export interface EditorParagraph {
  uid: string // 前端临时唯一 ID（用作 v-for key）
  type: ParagraphType
  content: string // 富文本 HTML 内容
  heading?: string // 段落小标题
  media_url?: string // 图片/视频 URL
  caption?: string // 媒体说明文字
}

/** 编辑器完整状态 */
export interface EditorState {
  postId: string | null // null = 新建
  title: string
  subtitles: string[]
  introduction: string
  paragraphs: EditorParagraph[]
  coverUrl: string
  tags: string[]
  requiredLevel: number
}

let uidCounter = 0
function generateUid(): string {
  return `para_${Date.now()}_${++uidCounter}`
}

export function useParagraphEditor() {
  const message = useMessage()

  // ── 状态 ──
  const postId = ref<string | null>(null)
  const title = ref('')
  const subtitles = ref<string[]>([])
  const introduction = ref<string>('')
  const paragraphs = ref<EditorParagraph[]>([])
  const coverUrl = ref('')
  const tags = ref<string[]>([])
  const requiredLevel = ref(5)
  const loading = ref(false)
  const saving = ref(false)
  const activeParagraphUid = ref<string | null>(null) // 当前聚焦的段落
  const pipelineProgress = ref<PipelineProgress | null>(null) // 流水线进度

  /** 是否编辑中（vs 新建） */
  const isEdit = computed(() => postId.value !== null)

  // ── 段落操作 ──

  /** 添加一个段落 */
  function addParagraph(type: ParagraphType = 'text', index?: number) {
    const para: EditorParagraph = {
      uid: generateUid(),
      type,
      content: ''
    }
    if (index !== undefined) {
      paragraphs.value.splice(index, 0, para)
    } else {
      paragraphs.value.push(para)
    }
    return para
  }

  /** 删除一个段落 */
  function removeParagraph(uid: string) {
    const idx = paragraphs.value.findIndex((p) => p.uid === uid)
    if (idx !== -1) {
      paragraphs.value.splice(idx, 1)
      if (activeParagraphUid.value === uid) {
        activeParagraphUid.value = null
      }
    }
  }

  /** 上移段落 */
  function moveParagraphUp(uid: string) {
    const idx = paragraphs.value.findIndex((p) => p.uid === uid)
    if (idx > 0) {
      const item = paragraphs.value[idx]!
      paragraphs.value.splice(idx, 1)
      paragraphs.value.splice(idx - 1, 0, item)
    }
  }

  /** 下移段落 */
  function moveParagraphDown(uid: string) {
    const idx = paragraphs.value.findIndex((p) => p.uid === uid)
    if (idx < paragraphs.value.length - 1) {
      const item = paragraphs.value[idx]!
      paragraphs.value.splice(idx, 1)
      paragraphs.value.splice(idx + 1, 0, item)
      paragraphs.value.splice(idx, 1)
      paragraphs.value.splice(idx + 1, 0, item)
    }
  }

  /** 拖拽移动段落：将 uid 移动到 targetUid 所在位置 */
  function moveParagraphTo(uid: string, targetUid: string) {
    if (uid === targetUid) return
    const fromIdx = paragraphs.value.findIndex((p) => p.uid === uid)
    const toIdx = paragraphs.value.findIndex((p) => p.uid === targetUid)
    if (fromIdx === -1 || toIdx === -1) return
    const [item] = paragraphs.value.splice(fromIdx, 1)
    const adjustedTo = fromIdx < toIdx ? toIdx - 1 : toIdx
    paragraphs.value.splice(adjustedTo, 0, item!)
  }

  /** 切换段落类型 */
  function setParagraphType(uid: string, type: ParagraphType) {
    const para = paragraphs.value.find((p) => p.uid === uid)
    if (para) {
      para.type = type
      // 切到 image/video 时清理旧 content
      if (type === 'image' || type === 'video') {
        para.content = ''
      }
    }
  }

  /** 更新段落内容 */
  function updateParagraphContent(uid: string, content: string) {
    const para = paragraphs.value.find((p) => p.uid === uid)
    if (para) para.content = content
  }

  /** 更新段落媒体 URL */
  function updateParagraphMediaUrl(uid: string, url: string) {
    const para = paragraphs.value.find((p) => p.uid === uid)
    if (para) para.media_url = url
  }

  /** 更新段落说明文字 */
  function updateParagraphCaption(uid: string, caption: string) {
    const para = paragraphs.value.find((p) => p.uid === uid)
    if (para) para.caption = caption
  }

  // ── 副标题操作 ──

  function addSubtitle() {
    subtitles.value.push('')
  }

  function removeSubtitle(index: number) {
    subtitles.value.splice(index, 1)
  }

  function updateSubtitle(index: number, value: string) {
    subtitles.value[index] = value
  }

  // ── 引言（富文本） ──

  function updateIntroduction(val: string) {
    introduction.value = val
  }

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

      // 解析引言（富文本）
      introduction.value = typeof post.introduction === 'string' ? post.introduction : ''

      // 加载段落
      const paraList = await getPostParagraphsApi(id, { limit: 200, offset: 0 })
      paragraphs.value = paraList.map((p: ParagraphData) => ({
        uid: generateUid(),
        type: (p.type as ParagraphType) || 'text',
        content: p.content || '',
        heading: p.heading,
        media_url: p.media_url,
        caption: p.caption
      }))
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
    introduction.value = ''
    paragraphs.value = [
      {
        uid: generateUid(),
        type: 'text',
        content: ''
      }
    ]
    coverUrl.value = ''
    tags.value = []
    requiredLevel.value = 5
  }

  /** 执行流水线并返回归一化结果 */
  async function runNormalization(alteredParagraphs: EditorParagraph[]): Promise<PipelineResult> {
    const result = await runPipeline(alteredParagraphs, 'content.md', {
      source: 'manual',
      onProgress: (p) => {
        pipelineProgress.value = { ...p }
      }
    })
    return result
  }

  /** 保存帖子 */
  async function save() {
    if (!title.value.trim()) {
      message.warning('标题不能为空')
      return false
    }

    saving.value = true
    try {
      // 先运行流水线：重新归一化段落结构 + 清理
      pipelineProgress.value = null
      const pipelineResult = await runNormalization(paragraphs.value)

      // 用归一化后的结果更新编辑器状态
      if (pipelineResult.title) {
        title.value = pipelineResult.title
      }
      if (pipelineResult.introduction && !introduction.value) {
        introduction.value = pipelineResult.introduction
      }
      if (pipelineResult.meta?.tags) {
        tags.value = [...new Set([...tags.value, ...pipelineResult.meta.tags])]
      }

      // 构建保存数据
      const paragraphData = pipelineResult.paragraphs.map((p) => ({
        content: p.content,
        type: p.type,
        ...(p.heading ? { heading: p.heading } : {}),
        ...(p.media_url ? { media_url: p.media_url } : {}),
        ...(p.caption ? { caption: p.caption } : {})
      }))

      const introductionData = introduction.value.trim().length > 0 ? introduction.value : undefined

      const payload: CreatePostPayload = {
        title: title.value.trim(),
        subtitles: subtitles.value.filter((s) => s.trim()),
        introduction: introductionData,
        paragraphs: paragraphData,
        tags: tags.value,
        required_level: requiredLevel.value,
        ...(coverUrl.value ? { cover_url: coverUrl.value } : {})
      }

      if (isEdit.value) {
        await updatePostApi(postId.value!, payload)
        message.success('保存成功')
      } else {
        const display = await createPostApi(payload as CreatePostPayload)
        postId.value = display.id
        message.success('发布成功，帖子已提交审核')
      }

      // 用归一化后的段落替换编辑器内容（用户可见的段落变化）
      paragraphs.value = pipelineResult.paragraphs.map((p) => ({
        uid: generateUid(),
        type: p.type,
        content: p.content,
        heading: p.heading,
        media_url: p.media_url,
        caption: p.caption
      }))

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
    introduction,
    paragraphs,
    coverUrl,
    tags,
    requiredLevel,
    loading,
    saving,
    activeParagraphUid,
    isEdit,
    pipelineProgress,

    // 段落操作
    addParagraph,
    removeParagraph,
    moveParagraphUp,
    moveParagraphDown,
    moveParagraphTo,
    setParagraphType,
    updateParagraphContent,
    updateParagraphMediaUrl,
    updateParagraphCaption,

    // 副标题操作
    addSubtitle,
    removeSubtitle,
    updateSubtitle,

    // 引言操作
    updateIntroduction,

    // 生命周期
    loadPost,
    resetForNew,
    save
  }
}
