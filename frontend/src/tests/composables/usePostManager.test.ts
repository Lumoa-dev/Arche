import { describe, it, expect, vi, beforeEach } from 'vitest'
import { usePostManager } from '@/components/widgets/create/usePostManager'

// Mock API 模块
vi.mock('@/lib/services/api', () => ({
  getMyPostsApi: vi.fn(),
}))

// Mock ensurePostsCovers
vi.mock('@/lib/composables/useCoverLazyGenerator', () => ({
  ensurePostsCovers: vi.fn(),
}))

import { getMyPostsApi } from '@/lib/services/api'

describe('usePostManager', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('初始状态：空列表，loading 为 false，tab 为 all', () => {
    const manager = usePostManager()

    expect(manager.posts.value).toEqual([])
    expect(manager.loading.value).toBe(false)
    expect(manager.activeTab.value).toBe('all')
    expect(manager.filteredPosts.value).toEqual([])
  })

  it('statCards 初始状态返回全零统计', () => {
    const manager = usePostManager()
    const cards = manager.statCards.value

    expect(cards).toHaveLength(4)
    expect(cards[0]).toEqual({ label: '全部文章', value: 0, color: 'var(--primary-color)' })
    expect(cards[1]).toEqual({ label: '已发布', value: 0, color: 'var(--success-color)' })
    expect(cards[2]).toEqual({ label: '草稿', value: 0, color: 'var(--accent-yellow)' })
    expect(cards[3]).toEqual({ label: '总阅读', value: 0, color: 'var(--accent-color)' })
  })

  it('fetchData 加载帖子列表', async () => {
    const mockPosts = [
      { id: '1', title: 'Post 1', status: 'published', views: 100 },
      { id: '2', title: 'Post 2', status: 'draft', views: 0 },
    ]
    vi.mocked(getMyPostsApi).mockResolvedValue({ list: mockPosts, total: 2 })

    const manager = usePostManager()
    await manager.fetchData()

    expect(manager.posts.value).toHaveLength(2)
    expect(manager.loading.value).toBe(false)
    expect(manager.statCards.value[0].value).toBe(2) // 全部文章 = 2
  })

  it('fetchData 失败时 posts 为空', async () => {
    vi.mocked(getMyPostsApi).mockRejectedValue(new Error('Network error'))

    const manager = usePostManager()
    await manager.fetchData()

    expect(manager.posts.value).toEqual([])
    expect(manager.loading.value).toBe(false)
  })

  it('filteredPosts 按 published 筛选', async () => {
    const mockPosts = [
      { id: '1', title: 'Published', status: 'published', views: 10 },
      { id: '2', title: 'Draft', status: 'draft', views: 0 },
      { id: '3', title: 'Unknown', views: 5 },
    ]
    vi.mocked(getMyPostsApi).mockResolvedValue({ list: mockPosts, total: 3 })

    const manager = usePostManager()
    await manager.fetchData()

    manager.activeTab.value = 'published'
    expect(manager.filteredPosts.value).toHaveLength(1)
    expect(manager.filteredPosts.value[0]!.title).toBe('Published')
  })

  it('filteredPosts 按 draft 筛选', async () => {
    const mockPosts = [
      { id: '1', title: 'Published', status: 'published', views: 10 },
      { id: '2', title: 'Draft', status: 'draft', views: 0 },
    ]
    vi.mocked(getMyPostsApi).mockResolvedValue({ list: mockPosts, total: 2 })

    const manager = usePostManager()
    await manager.fetchData()

    manager.activeTab.value = 'draft'
    expect(manager.filteredPosts.value).toHaveLength(1)
    expect(manager.filteredPosts.value[0]!.title).toBe('Draft')
  })

  it('filteredPosts 状态为 unknown 时归为 draft', async () => {
    const mockPosts = [
      { id: '1', title: 'No Status', views: 0 },
    ]
    vi.mocked(getMyPostsApi).mockResolvedValue({ list: mockPosts, total: 1 })

    const manager = usePostManager()
    await manager.fetchData()

    manager.activeTab.value = 'draft'
    expect(manager.filteredPosts.value).toHaveLength(1)
  })

  it('statCards 显示正确统计', async () => {
    const mockPosts = [
      { id: '1', title: 'Published', status: 'published', views: 100 },
      { id: '2', title: 'Draft', status: 'draft', views: 0 },
      { id: '3', title: 'Another Published', status: 'published', views: 50 },
    ]
    vi.mocked(getMyPostsApi).mockResolvedValue({ list: mockPosts, total: 3 })

    const manager = usePostManager()
    await manager.fetchData()

    const cards = manager.statCards.value
    expect(cards[0].value).toBe(3)  // 全部
    expect(cards[1].value).toBe(2)  // 已发布
    expect(cards[2].value).toBe(1)  // 草稿
    expect(cards[3].value).toBe(150) // 总阅读
  })

  it('refreshPosts 重新加载数据', async () => {
    vi.mocked(getMyPostsApi).mockResolvedValue({ list: [], total: 0 })

    const manager = usePostManager()
    await manager.refreshPosts()

    expect(getMyPostsApi).toHaveBeenCalledTimes(1)
  })

  it('fetchData 调用时传递正确的参数', async () => {
    vi.mocked(getMyPostsApi).mockResolvedValue({ list: [], total: 0 })

    const manager = usePostManager()
    await manager.fetchData()

    expect(getMyPostsApi).toHaveBeenCalledWith(
      { page: 1, page_size: 50, sort_by: 'created_at' },
      { silent: true, skipAuthLogout: true }
    )
  })
})