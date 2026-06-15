import { describe, it, expect, vi, beforeEach } from 'vitest'

vi.mock('@/lib/services/request', () => ({
  get: vi.fn(),
  post: vi.fn(),
  put: vi.fn(),
  del: vi.fn()
}))

beforeEach(() => {
  vi.clearAllMocks()
})

describe('blog API', () => {
  it('getBlogPostsApi 发送正确 URL 和方法', async () => {
    const { getBlogPostsApi } = await import('@/lib/services/api/blog')
    const { get } = await import('@/lib/services/request')
    vi.mocked(get).mockResolvedValue({ items: [], total: 0 })

    await getBlogPostsApi({ page: 1, page_size: 20 })
    expect(get).toHaveBeenCalledWith('/blog/posts', { page: 1, page_size: 20 }, undefined)
  })

  it('getPostBySlugApi 拼接正确路径', async () => {
    const { getPostBySlugApi } = await import('@/lib/services/api/blog')
    const { get } = await import('@/lib/services/request')
    vi.mocked(get).mockResolvedValue({ id: '1', title: 'test' })

    await getPostBySlugApi('hello-world')
    expect(get).toHaveBeenCalledWith('/blog/posts/hello-world', undefined, undefined)
  })

  it('getPostByIdApi 拼接正确路径', async () => {
    const { getPostByIdApi } = await import('@/lib/services/api/blog')
    const { get } = await import('@/lib/services/request')
    vi.mocked(get).mockResolvedValue({ id: '1' })

    await getPostByIdApi('abc-123')
    expect(get).toHaveBeenCalledWith('/blog/posts/by-id/abc-123', undefined, undefined)
  })

  it('createPostApi 发送 POST 请求', async () => {
    const { createPostApi } = await import('@/lib/services/api/blog')
    const { post } = await import('@/lib/services/request')
    vi.mocked(post).mockResolvedValue({ id: '1' })

    const payload = { title: 'Test', content: 'Hello', tags: ['tag1'] }
    await createPostApi(payload)
    expect(post).toHaveBeenCalledWith('/blog/posts', payload, undefined)
  })

  it('updatePostApi 发送 PUT 请求', async () => {
    const { updatePostApi } = await import('@/lib/services/api/blog')
    const { put } = await import('@/lib/services/request')
    vi.mocked(put).mockResolvedValue({ id: '1' })

    await updatePostApi('post-1', { title: 'Updated' })
    expect(put).toHaveBeenCalledWith('/blog/posts/post-1', { title: 'Updated' }, undefined)
  })

  it('deletePostApi 发送 DELETE 请求', async () => {
    const { deletePostApi } = await import('@/lib/services/api/blog')
    const { del } = await import('@/lib/services/request')
    vi.mocked(del).mockResolvedValue(undefined)

    await deletePostApi('post-1')
    expect(del).toHaveBeenCalledWith('/blog/posts/post-1', undefined, undefined)
  })

  it('getPostCommentsApi 拼接正确路径', async () => {
    const { getPostCommentsApi } = await import('@/lib/services/api/blog')
    const { get } = await import('@/lib/services/request')
    vi.mocked(get).mockResolvedValue({ items: [], total: 0 })

    await getPostCommentsApi('post-1')
    expect(get).toHaveBeenCalledWith('/blog/posts/post-1/comments', undefined, undefined)
  })

  it('likePostApi 发送正确请求', async () => {
    const { likePostApi } = await import('@/lib/services/api/blog')
    const { post } = await import('@/lib/services/request')
    vi.mocked(post).mockResolvedValue(undefined)

    await likePostApi('post-1')
    expect(post).toHaveBeenCalledWith('/blog/posts/post-1/like', undefined, undefined)
  })

  it('getBlogTagsApi 发送正确请求', async () => {
    const { getBlogTagsApi } = await import('@/lib/services/api/blog')
    const { get } = await import('@/lib/services/request')
    vi.mocked(get).mockResolvedValue({ items: [], total: 0 })

    await getBlogTagsApi()
    expect(get).toHaveBeenCalledWith('/blog/tags', undefined, undefined)
  })

  it('normalizePaginated 正确处理 items→list 转换', async () => {
    const { getBlogPostsApi } = await import('@/lib/services/api/blog')
    const { get } = await import('@/lib/services/request')
    vi.mocked(get).mockResolvedValue({
      items: [{ id: '1', title: 'A', slug: 'a', content: '' }],
      total: 1
    })

    const result = await getBlogPostsApi()
    expect(result.list).toHaveLength(1)
    expect(result.total).toBe(1)
  })

  it('batchApproveApi 发送正确请求', async () => {
    const { batchApproveApi } = await import('@/lib/services/api/blog')
    const { post } = await import('@/lib/services/request')
    vi.mocked(post).mockResolvedValue(undefined)

    await batchApproveApi({ post_ids: ['1', '2'] })
    expect(post).toHaveBeenCalledWith(
      '/blog/moderation/batch-approve',
      { post_ids: ['1', '2'] },
      undefined
    )
  })
})
