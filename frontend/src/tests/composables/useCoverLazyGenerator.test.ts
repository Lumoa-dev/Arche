import { describe, it, expect, vi, beforeEach } from 'vitest'

// ── Mock 依赖（使用 vi.hoisted 确保在 hoisting 阶段可用）──
const { mockGenerateTextCover, mockUploadOssFileApi, mockUpdatePostApi, mockFetch } = vi.hoisted(
  () => {
    return {
      mockGenerateTextCover: vi.fn(),
      mockUploadOssFileApi: vi.fn(),
      mockUpdatePostApi: vi.fn(),
      mockFetch: vi.fn()
    }
  }
)

vi.mock('@/utils/generateTextCover', () => ({
  generateTextCover: mockGenerateTextCover
}))

vi.mock('@/services/api/oss', () => ({
  uploadOssFileApi: mockUploadOssFileApi
}))

vi.mock('@/services/api/blog', () => ({
  updatePostApi: mockUpdatePostApi
}))

// fetch 需要 mock，因为 ensurePostCover 内部用 fetch 将 dataURL 转 Blob
vi.stubGlobal('fetch', mockFetch)

import { ensurePostCover, ensurePostsCovers } from '@/components/logic/useCoverLazyGenerator'

/** 创建一个基础帖子对象 */
function createPost(overrides: Record<string, any> = {}): any {
  return {
    id: 'post-1',
    title: '测试文章',
    content: '正文内容',
    tags: ['技术'],
    cover_url: undefined,
    auto_cover_url: undefined,
    ...overrides
  }
}

describe('useCoverLazyGenerator', () => {
  beforeEach(() => {
    vi.clearAllMocks()

    // 默认 fetch 返回一个可生成 blob 的 Response
    mockFetch.mockResolvedValue({
      blob: () => Promise.resolve(new Blob(['fake-image'], { type: 'image/jpeg' }))
    })
  })

  describe('ensurePostCover', () => {
    it('已有 cover_url 时跳过处理，直接返回 cover_url', async () => {
      const post = createPost({ cover_url: '/existing-cover.jpg' })

      const result = await ensurePostCover(post)

      expect(result).toBe('/existing-cover.jpg')
      expect(mockGenerateTextCover).not.toHaveBeenCalled()
      expect(mockUploadOssFileApi).not.toHaveBeenCalled()
    })

    it('已有 auto_cover_url 时跳过处理，直接返回 auto_cover_url', async () => {
      const post = createPost({ auto_cover_url: '/auto-cover.jpg' })

      const result = await ensurePostCover(post)

      expect(result).toBe('/auto-cover.jpg')
      expect(mockGenerateTextCover).not.toHaveBeenCalled()
    })

    it('cover_url 和 auto_cover_url 同时存在时优先返回 auto_cover_url', async () => {
      const post = createPost({ cover_url: '/manual.jpg', auto_cover_url: '/auto.jpg' })

      const result = await ensurePostCover(post)

      expect(result).toBe('/auto.jpg')
    })

    it('post 为 null/undefined 时返回 null', async () => {
      const result = await ensurePostCover(null as any)
      expect(result).toBeNull()
    })

    it('缺少 id 或 title 时跳过', async () => {
      const result1 = await ensurePostCover(createPost({ id: '' }))
      expect(result1).toBeNull()

      const result2 = await ensurePostCover(createPost({ title: '' }))
      expect(result2).toBeNull()
    })

    it('demo 帖子跳过', async () => {
      const post = createPost({ id: 'demo-123' })

      const result = await ensurePostCover(post)
      expect(result).toBeNull()
    })

    it('正常流程：生成封面 → 上传 OSS → 持久化 → 更新本地对象', async () => {
      const post = createPost()
      mockGenerateTextCover.mockReturnValue('data:image/jpeg;base64,fake')
      mockUploadOssFileApi.mockResolvedValue({ data: { id: 'oss-file-1' } })
      mockUpdatePostApi.mockResolvedValue(undefined)

      const result = await ensurePostCover(post)

      expect(result).toBe('/api/oss/files/oss-file-1')
      // 检查生成了封面
      expect(mockGenerateTextCover).toHaveBeenCalledWith(post, true)
      // 检查上传了 OSS
      expect(mockUploadOssFileApi).toHaveBeenCalledTimes(1)
      const uploadedFile = mockUploadOssFileApi.mock.calls[0]![0] as File
      expect(uploadedFile.name).toBe('text-cover.jpg')
      expect(mockUploadOssFileApi.mock.calls[0]![1]).toBe(false)
      // 检查持久化到后端
      expect(mockUpdatePostApi).toHaveBeenCalledWith('post-1', {
        auto_cover_url: '/api/oss/files/oss-file-1'
      })
      // 检查更新了本地对象
      expect(post.auto_cover_url).toBe('/api/oss/files/oss-file-1')
    })

    it('上传 OSS 返回不含 id 时返回 null', async () => {
      const post = createPost()
      mockGenerateTextCover.mockReturnValue('data:image/jpeg;base64,fake')
      mockUploadOssFileApi.mockResolvedValue({ data: {} })

      const result = await ensurePostCover(post)

      expect(result).toBeNull()
      expect(mockUpdatePostApi).not.toHaveBeenCalled()
    })

    it('处理过程中抛出异常时返回 null', async () => {
      const post = createPost()
      mockGenerateTextCover.mockReturnValue('data:image/jpeg;base64,fake')
      mockUploadOssFileApi.mockRejectedValue(new Error('OSS 上传失败'))

      const result = await ensurePostCover(post)

      expect(result).toBeNull()
    })

    it('并发调用同一帖子时，重复请求被去重（processingPosts 防止并发）', async () => {
      const post = createPost()
      mockGenerateTextCover.mockReturnValue('data:image/jpeg;base64,fake')
      // 第一个请求的 fetch 永远不 resolve，模拟长时间操作
      mockFetch.mockReturnValue(new Promise(() => {}))

      // 同时发起两个并发请求（不 await 第一个，让其挂起）
      void ensurePostCover(post)
      const promise2 = ensurePostCover(post)

      // 第二个请求应该直接返回 null（已在处理中）
      const result2 = await promise2
      expect(result2).toBeNull()
      // generateTextCover 只被第一个请求触发了一次
      expect(mockGenerateTextCover).toHaveBeenCalledTimes(1)
    })
  })

  describe('ensurePostsCovers', () => {
    it('空数组直接返回', async () => {
      await ensurePostsCovers([])
      expect(mockGenerateTextCover).not.toHaveBeenCalled()
    })

    it('只处理缺少封面的帖子，已有封面的跳过', async () => {
      mockGenerateTextCover.mockReturnValue('data:image/jpeg;base64,fake')
      mockUploadOssFileApi.mockResolvedValue({ data: { id: 'f' } })
      mockUpdatePostApi.mockResolvedValue(undefined)

      const posts = [createPost({ id: 'p1', cover_url: '/exists.jpg' }), createPost({ id: 'p2' })]

      await ensurePostsCovers(posts)

      // 只有 p2 被处理
      expect(mockGenerateTextCover).toHaveBeenCalledTimes(1)
      expect(mockGenerateTextCover).toHaveBeenCalledWith(posts[1], true)
    })

    it('demo 帖子被过滤掉', async () => {
      const posts = [createPost({ id: 'demo-abc' })]

      await ensurePostsCovers(posts)

      expect(mockGenerateTextCover).not.toHaveBeenCalled()
    })
  })
})
