import { describe, it, expect, vi, beforeEach } from 'vitest'
import { usePostManager } from '@/components/widgets/create/usePostManager'

// Mock API
vi.mock('@/lib/services/api', () => ({
  getMyPostsApi: vi.fn()
}))

// Mock cover lazy generator
vi.mock('@/lib/composables/useCoverLazyGenerator', () => ({
  ensurePostsCovers: vi.fn()
}))

beforeEach(() => {
  vi.clearAllMocks()
})

describe('usePostManager', () => {
  it('初始状态：空列表、all tab、loading false', () => {
    const manager = usePostManager()

    expect(manager.posts.value).toEqual([])
    expect(manager.loading.value).toBe(false)
    expect(manager.activeTab.value).toBe('all')
  })

  it('statCards 返回正确的统计信息', () => {
    const manager = usePostManager()

    // 初始状态：所有计数为 0
    expect(manager.statCards.value).toHaveLength(4)
    expect(manager.statCards.value[0].label).toBe('全部文章')
    expect(manager.statCards.value[0].value).toBe(0)
    expect(manager.statCards.value[1].label).toBe('已发布')
    expect(manager.statCards.value[2].label).toBe('草稿')
    expect(manager.statCards.value[3].label).toBe('总阅读')
  })

  it('statCards 反映 posts 数据变化', () => {
    const manager = usePostManager()
    manager.posts.value = [
      { id: '1', title: 'A', status: 'published', views: 100 } as any,
      { id: '2', title: 'B', status: 'draft', views: 0 } as any,
      { id: '3', title: 'C', status: 'published', views: 50 } as any
    ]

    // 通过 statCards 间接验证统计结果
    expect(manager.statCards.value[0].value).toBe(3)  // 全部文章
    expect(manager.statCards.value[1].value).toBe(2)  // 已发布
    expect(manager.statCards.value[2].value).toBe(1)  // 草稿
    expect(manager.statCards.value[3].value).toBe(150) // 总阅读
  })

  it('filteredPosts 按 activeTab 过滤', () => {
    const manager = usePostManager()
    manager.posts.value = [
      { id: '1', title: 'Pub', status: 'published' } as any,
      { id: '2', title: 'Draft', status: 'draft' } as any,
      { id: '3', title: 'Default', status: undefined } as any
    ]

    // all tab
    manager.activeTab.value = 'all'
    expect(manager.filteredPosts.value).toHaveLength(3)

    // published tab
    manager.activeTab.value = 'published'
    expect(manager.filteredPosts.value).toHaveLength(1)
    expect(manager.filteredPosts.value[0].title).toBe('Pub')

    // draft tab
    manager.activeTab.value = 'draft'
    expect(manager.filteredPosts.value).toHaveLength(2) // 'draft' + undefined 视为 draft
  })

  it('fetchData 获取帖子列表', async () => {
    const { getMyPostsApi } = await import('@/lib/services/api')
    const mockPosts = {
      list: [
        { id: '1', title: 'Post 1', status: 'published', views: 10 },
        { id: '2', title: 'Post 2', status: 'draft', views: 0 }
      ],
      total: 2
    }
    vi.mocked(getMyPostsApi).mockResolvedValue(mockPosts)

    const manager = usePostManager()
    await manager.fetchData()

    expect(manager.posts.value).toHaveLength(2)
    expect(manager.loading.value).toBe(false)
    expect(getMyPostsApi).toHaveBeenCalledWith(
      { page: 1, page_size: 50, sort_by: 'created_at' },
      { silent: true, skipAuthLogout: true }
    )
  })

  it('fetchData 失败时 posts 为空', async () => {
    const { getMyPostsApi } = await import('@/lib/services/api')
    vi.mocked(getMyPostsApi).mockRejectedValue(new Error('Network error'))

    const manager = usePostManager()
    await manager.fetchData()

    expect(manager.posts.value).toEqual([])
    expect(manager.loading.value).toBe(false)
  })

  it('refreshPosts 调用 fetchData', async () => {
    const { getMyPostsApi } = await import('@/lib/services/api')
    vi.mocked(getMyPostsApi).mockResolvedValue({ list: [], total: 0 })

    const manager = usePostManager()
    await manager.refreshPosts()

    expect(getMyPostsApi).toHaveBeenCalled()
  })

  it('statCards 随 posts 变化而更新', () => {
    const manager = usePostManager()

    expect(manager.statCards.value[0].value).toBe(0)
    expect(manager.statCards.value[1].value).toBe(0)
    expect(manager.statCards.value[2].value).toBe(0)
    expect(manager.statCards.value[3].value).toBe(0)

    // 添加 posts
    manager.posts.value = [
      { id: '1', views: 10, status: 'published' } as any,
      { id: '2', views: 20, status: 'draft' } as any
    ]

    expect(manager.statCards.value[0].value).toBe(2)  // 全部文章
    expect(manager.statCards.value[1].value).toBe(1)  // 已发布
    expect(manager.statCards.value[2].value).toBe(1)  // 草稿
    expect(manager.statCards.value[3].value).toBe(30) // 总阅读
  })
})