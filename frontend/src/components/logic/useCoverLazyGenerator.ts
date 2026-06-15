/**
 * 帖子封面懒加载生成 composable。
 *
 * 当帖子没有手动封面（cover_url）且没有自动生成封面（auto_cover_url）时，
 * 按需在浏览器端生成文字封面 → 上传 OSS → 持久化回后端。
 */
import { generateTextCover } from '@/lib/utils/generateTextCover'
import { uploadOssFileApi } from '@/components/logic/api/oss'
import { updatePostApi, type BlogPost } from '@/components/logic/api/blog'

/** 正在处理中的帖子 ID 集合，防止并发重复触发 */
const processingPosts = new Set<string>()

/**
 * 为单篇缺少封面的帖子生成文字封面。
 * - 浏览器 Canvas 生成 → dataURL → Blob → 上传 OSS → 持久化到后端
 * - 同时更新传入的 post 对象（响应式），使 UI 自动更新
 *
 * @returns 生成的封面 URL，失败返回 null
 */
export async function ensurePostCover(post: BlogPost): Promise<string | null> {
  // 已有封面 → 跳过
  if (!post || post.cover_url || post.auto_cover_url) {
    return post?.auto_cover_url ?? post?.cover_url ?? null
  }
  // 缺少必要字段或为 demo/占位数据 → 跳过
  if (!post.id || !post.title || post.id.startsWith('demo-')) {
    return null
  }
  // 防止并发重复处理同一帖子
  if (processingPosts.has(post.id)) return null
  processingPosts.add(post.id)

  try {
    // 1. 生成 Canvas 文字封面 → dataURL
    const dataUrl = generateTextCover(post, true)

    // 2. 转 Blob → File → 上传 OSS
    const blob = await fetch(dataUrl).then((r) => r.blob())
    const file = new File([blob], 'text-cover.jpg', { type: 'image/jpeg' })
    const resp = await uploadOssFileApi(file, false)
    const respData = resp as unknown as { data?: { id: string } }
    if (!respData?.data?.id) return null

    const autoCoverUrl = `/api/oss/files/${respData.data.id}`

    // 3. 持久化到后端
    await updatePostApi(post.id, { auto_cover_url: autoCoverUrl })

    // 4. 更新本地响应式对象，UI 自动重新渲染
    post.auto_cover_url = autoCoverUrl

    return autoCoverUrl
  } catch (e) {
    console.warn('[useCoverLazyGenerator] 为帖子生成封面失败:', post.id, e)
    return null
  } finally {
    processingPosts.delete(post.id)
  }
}

/**
 * 为一批帖子批量触发懒加载封面生成。
 * 逐个处理以避免并发 OSS 上传过多。
 */
export async function ensurePostsCovers(posts: BlogPost[]): Promise<void> {
  if (!posts || posts.length === 0) return

  const needCover = posts.filter(
    (p) => p && !p.cover_url && !p.auto_cover_url && p.id && p.title && !p.id.startsWith('demo-')
  )
  if (needCover.length === 0) return

  // 逐个处理，间隔 200ms 避免 OSS 并发压力
  for (const post of needCover) {
    await ensurePostCover(post)
    await new Promise((r) => setTimeout(r, 200))
  }
}
