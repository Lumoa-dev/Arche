/**
 * usePostManager 单元测试
 *
 * 测试原则：
 * - 使用 vitest mock 隔离 API 调用
 * - 覆盖帖子列表管理、筛选、统计计算
 * - 每个测试独立
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { nextTick } from 'vue'
import { usePostManager } from '@/components/widgets/create/usePostManager'

// ── Mock API 模块 ──
vi.mock('@/lib/services/api', () => ({
  getMyPostsApi: vi.fn()
}))

// ── Mock cover lazy generator ──
vi.mock('@/lib/composables/useCoverLazyGenerator', () => ({
  ensurePostsCovers: vi.fn()
}))

import { getMyPostsApi } from '@/lib/services/api'

// 辅助函数：创建 mock 帖子
function createMockPost(overrides: Record<string, any> = {}) {
  return {
    id: overrides.id || 'post-1',
    title: overrides.title || '测试帖子',
    status: overrides.status || 'draft',
    views: overrides.views ?? 0,
    ...overrides
  }
}

describe('usePostManager', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  // ── 初始状态 ──

  it('初始状态：posts 为空，loading 为 false，activeTab 为 all', () => {
    const manager = usePostManager()

    expect(manager.posts.value).toEqual([])
    expect(manager.loading.value).toBe(false)
    expect(manager.activeTab.value).toBe('all')
  })

  // ── filteredPosts ──

  it('activeTab 为 all 时返回所有帖子', () => {
    const manager = usePostManager()
    manager.posts.value = [
      createMockPost({ id: '1', status: 'published' }),
      createMockPost({ id: '2', status: 'draft' }),
      createMockPost({ id: '3', status: 'draft' })
    ]

    expect(manager.filteredPosts.value).toHaveLength(3)
  })

  it('activeTab 为 published 时只返回已发布帖子', () => {
    const manager = usePostManager()
    manager.posts.value = [
      createMockPost({ id: '1', status: 'published' }),
      createMockPost({ id: '2', status: 'draft' }),
      createMockPost({ id: '3', status: 'published' })
    ]
    manager.activeTab.value = 'published'

    expect(manager.filteredPosts.value).toHaveLength(2)
    expect(manager.filteredPosts.value.every((p) => p.status === 'published')).toBe(true)
  })

  it('activeTab 为 draft 时只返回草稿帖子', () => {
    const manager = usePostManager()
    manager.posts.value = [
      createMockPost({ id: '1', status: 'published' }),
      createMockPost({ id: '2', status: 'draft' }),
      createMockPost({ id: '3', status: 'draft' })
    ]
    manager.activeTab.value = 'draft'

    expect(manager.filteredPosts.value).toHaveLength(2)
    expect(manager.filteredPosts.value.every((p) => (p.status || 'draft') === 'draft')).toBe(true)
  })

  it('activeTab 为 draft 时无 status 的帖子被视为 draft', () => {
    const manager = usePostManager()
    manager.posts.value = [
      createMockPost({ id: '1', status: undefined }),
      createMockPost({ id: '2', status: 'published' })
    ]
    manager.activeTab.value = 'draft'

    expect(manager.filteredPosts.value).toHaveLength(1)
    expect(manager.filteredPosts.value[0].id).toBe('1')
  })

  it('activeTab 切换后 filteredPosts 正确更新', () => {
    const manager = usePostManager()
    manager.posts.value = [
      createMockPost({ id: '1', status: 'published' }),
      createMockPost({ id: '2', status: 'draft' })
    ]

    expect(manager.filteredPosts.value).toHaveLength(2)

    manager.activeTab.value = 'published'
    expect(manager.filteredPosts.value).toHaveLength(1)
    expect(manager.filteredPosts.value[0].id).toBe('1')

    manager.activeTab.value = 'draft'
    expect(manager.filteredPosts.value).toHaveLength(1)
    expect(manager.filteredPosts.value[0].id).toBe('2')
  })

  // ── statCards ──

  it('statCards 计算全部帖子、已发布、草稿和总阅读数', () => {
    const manager = usePostManager()
    manager.posts.value = [
      createMockPost({ id: '1', status: 'published', views: 100 }),
      createMockPost({ id: '2', status: 'draft', views: 50 }),
      createMockPost({ id: '3', status: 'published', views: 200 })
    ]

    const cards = manager.statCards.value

    expect(cards).toHaveLength(4)
    expect(cards[0]).toEqual(
      expect.objectContaining({ label: '全部文章', value: 3 })
    )
    expect(cards[1]).toEqual(
      expect.objectContaining({ label: '已发布', value: 2 })
    )
    expect(cards[2]).toEqual(
      expect.objectContaining({ label: '草稿', value: 1 })
    )
    expect(cards[3]).toEqual(
      expect.objectContaining({ label: '总阅读', value: 350 })
    )
  })

  it('帖子列表为空时 statCards 全为 0', () => {
    const manager = usePostManager()
    manager.posts.value = []

    const cards = manager.statCards.value

    expect(cards.every((c) => c.value === 0)).toBe(true)
  })

  it('views 为 undefined 时总阅读数正确计算', () => {
    const manager = usePostManager()
    manager.posts.value = [
      createMockPost({ id: '1', views: undefined }),
      createMockPost({ id: '2', views: 10 })
    ]

    expect(manager.statCards.value[3].value).toBe(10)
  })

  // ── fetchData ──

  it('fetchData() 从 API 获取帖子列表', async () => {
    const mockPosts = [
      createMockPost({ id: '1', status: 'published' }),
      createMockPost({ id: '2', status: 'draft' })
    ]
    vi.mocked(getMyPostsApi).mockResolvedValue({ list: mockPosts, total: 2 })

    const manager = usePostManager()
    await manager.fetchData()

    expect(manager.posts.value).toHaveLength(2)
    expect(manager.loading.value).toBe(false)
    expect(getMyPostsApi).toHaveBeenCalledWith(
      { page: 1, page_size: 50, sort_by: 'created_at' },
      { silent: true, skipAuthLogout: true }
    )
  })

  it('fetchData() 加载过程中 loading 为 true', async () => {
    let resolvePromise: (value: any) => void
    const promise = new Promise((resolve) => {
      resolvePromise = resolve
    })
    vi.mocked(getMyPostsApi).mockReturnValue(promise as any)

    const manager = usePostManager()
    const fetchPromise = manager.fetchData()

    expect(manager.loading.value).toBe(true)

    resolvePromise!({ list: [], total: 0 })
    await fetchPromise
    expect(manager.loading.value).toBe(false)
  })

  it('fetchData() API 失败时 posts 为空数组', async () => {
    vi.mocked(getMyPostsApi).mockRejectedValue(new Error('网络错误'))

    const manager = usePostManager()
    manager.posts.value = [createMockPost()] // 先设置旧数据

    await manager.fetchData()

    expect(manager.posts.value).toEqual([])
    expect(manager.loading.value).toBe(false)
  })

  it('fetchData() API 返回空列表时 posts 正确更新', async () => {
    vi.mocked(getMyPostsApi).mockResolvedValue({ list: [], total: 0 })

    const manager = usePostManager()
    await manager.fetchData()

    expect(manager.posts.value).toEqual([])
  })

  // ── refreshPosts ──

  it('refreshPosts() 调用 fetchData()', async () => {
    vi.mocked(getMyPostsApi).mockResolvedValue({ list: [], total: 0 })

    const manager = usePostManager()
    await manager.refreshPosts()

    expect(getMyPostsApi).toHaveBeenCalledTimes(1)
  })
})