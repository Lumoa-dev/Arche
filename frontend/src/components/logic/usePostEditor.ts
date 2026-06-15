/**
 * usePostEditor — 编辑器状态管理和保存逻辑
 *
 * 负责编辑模式的开关、帖子创建/编辑切换、标签管理、
 * 封面上传、素材暂存和最终的保存/发布流程。
 */
import { ref } from 'vue'
import { useMessage } from 'naive-ui'
import { useLocalFiles } from '@/components/logic/useLocalFiles'
import {
  createPostApi,
  updatePostApi,
  uploadPostFileApi,
  type BlogPost,
  type CreatePostPayload
} from '@/components/logic/api'
import { uploadOssFileApi } from '@/components/logic/api/oss'
import { generateTextCover } from '@/lib/utils/generateTextCover'

export function usePostEditor() {
  const message = useMessage()
  const { stagedFiles, stageFiles, getReferencedFiles, clearStaged } = useLocalFiles()

  const isOpen = ref(false)
  const isNew = ref(false)
  const editingPost = ref<BlogPost | null>(null)
  const tags = ref<string[]>([])
  const access = ref<number>(5)
  const coverUrl = ref('')
  const coverFile = ref<File | null>(null)
  const saving = ref(false)
  const pendingImport = ref<any>(null)

  /** 打开新建帖子编辑器 */
  function openNew() {
    isNew.value = true
    editingPost.value = null
    tags.value = []
    access.value = 5
    coverUrl.value = ''
    coverFile.value = null
    clearStaged()
    isOpen.value = true
  }

  /** 打开已有帖子的编辑器 */
  function openEdit(post: BlogPost) {
    isNew.value = false
    editingPost.value = post
    tags.value = [...(post.tags || [])]
    access.value = (post.required_level as number) ?? 5
    coverUrl.value = post.cover_url || ''
    isOpen.value = true
  }

  /** 关闭编辑器并重置所有状态 */
  function close() {
    isOpen.value = false
    isNew.value = false
    editingPost.value = null
    tags.value = []
    coverUrl.value = ''
    coverFile.value = null
    clearStaged()
    pendingImport.value = null
  }

  /** 切换到另一篇帖子编辑 */
  function switchPost(post: BlogPost) {
    isNew.value = false
    editingPost.value = post
    tags.value = [...(post.tags || [])]
    access.value = (post.required_level as number) ?? 5
    coverUrl.value = post.cover_url || ''
  }

  /** 添加标签 */
  function addTag(tag: string) {
    if (tag && !tags.value.includes(tag)) {
      tags.value.push(tag)
    }
  }

  /** 移除标签 */
  function removeTag(tag: string) {
    tags.value = tags.value.filter((t) => t !== tag)
  }

  /**
   * 保存/发布帖子。
   * @param title - 标题
   * @param content - HTML 正文
   * @param postManagerRefresh - 保存后刷新列表的回调
   */
  async function save(title: string, content: string, postManagerRefresh?: () => Promise<void>) {
    if (!title || !content) return
    saving.value = true
    try {
      // 1. 上传所有被正文引用的暂存文件
      const refFiles = getReferencedFiles(content)
      const refMap = new Map<number, string>()
      for (const sf of refFiles) {
        const resp = await uploadOssFileApi(sf.file, false)
        const respData = resp as unknown as { data?: { id: string } }
        const fileId = respData?.data?.id
        if (fileId) {
          refMap.set(sf.index, `/api/oss/files/${fileId}`)
        }
      }

      // 2. 上传封面（如果是本地 blob）
      let finalCoverUrl = coverUrl.value
      if (coverFile.value && coverUrl.value.startsWith('blob:')) {
        const resp = await uploadOssFileApi(coverFile.value, false)
        const respData = resp as unknown as { data?: { id: string } }
        const fileId = respData?.data?.id
        if (fileId) {
          finalCoverUrl = `/api/oss/files/${fileId}`
        }
      }

      // 2.5 没有封面 → 自动生成文字封面并上传 OSS
      let autoCoverUrl = ''
      if (!finalCoverUrl && title) {
        const textCoverDataUrl = generateTextCover(
          {
            id: '',
            slug: '',
            title,
            intro: undefined,
            content,
            tags: tags.value
          } as BlogPost,
          true
        )
        const blob = await fetch(textCoverDataUrl).then((r) => r.blob())
        const file = new File([blob], 'text-cover.jpg', { type: 'image/jpeg' })
        const resp = await uploadOssFileApi(file, false)
        const respData = resp as unknown as { data?: { id: string } }
        if (respData?.data?.id) {
          autoCoverUrl = `/api/oss/files/${respData.data.id}`
        }
      }

      // 3. 替换正文中的 [#N] 为实际 OSS URL
      let finalContent = content
      for (const [index, ossUrl] of refMap) {
        finalContent = finalContent.replace(
          new RegExp(`\\[#${index}\\]`, 'g'),
          `![图片](${ossUrl})`
        )
      }

      // 4. 发送保存请求
      const isEdit = !!editingPost.value
      const payload: CreatePostPayload = {
        title,
        content: finalContent,
        ...(finalCoverUrl ? { cover_url: finalCoverUrl } : {}),
        ...(autoCoverUrl ? { auto_cover_url: autoCoverUrl } : {}),
        tags: tags.value,
        required_level: access.value
      }

      if (isEdit) {
        await updatePostApi(editingPost.value!.id, payload)
        message.success('保存成功')
        await postManagerRefresh?.()
      } else {
        await createPostApi(payload)
        message.success('发布成功，帖子已提交审核')
        await postManagerRefresh?.()
        close()
      }
    } catch {
      message.error('保存失败，请重试')
    } finally {
      saving.value = false
    }
  }

  /** 导入 .txt/.md 文件并进入编辑模式 */
  async function importFile(file: File): Promise<boolean> {
    try {
      const result = await uploadPostFileApi(file, { silent: true })
      isNew.value = true
      editingPost.value = null
      tags.value = (result as any)?.tags || []
      access.value = 5
      pendingImport.value = result
      isOpen.value = true
      message.success('文件导入成功')
      return true
    } catch {
      message.error('文件导入失败，请重试')
      return false
    }
  }

  /** 处理 CoverUploader 传回的本地封面文件 */
  function handleCoverFile(file: File) {
    coverFile.value = file
  }

  return {
    isOpen,
    isNew,
    editingPost,
    tags,
    access,
    coverUrl,
    coverFile,
    stagedFiles,
    saving,
    pendingImport,
    openNew,
    openEdit,
    close,
    save,
    switchPost,
    addTag,
    removeTag,
    importFile,
    handleCoverFile,
    stageFiles
  }
}
