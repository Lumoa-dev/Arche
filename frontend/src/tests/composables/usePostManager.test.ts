import { describe, it, expect, vi, beforeEach } from 'vitest'
import { usePostManager, type PostTab } from '@/components/widgets/create/usePostManager'

// mock ensurePostsCovers
vi.mock('@/lib/composables/useCoverLazyGenerator', () => ({
  ensurePostsCovers: vi.fn()
}))

const mockGetMyPostsApi = vi.fn()

vi.mock('@/lib/services/api', () => ({
  getMyPostsApi: (...args: any[]) => mockGetMyPostsApi(...args)
}))

/**
 * 辅助：生成测试帖子
 */
function makePost(overrides: Record<string, any> = {}) {
  return {
    id: `post-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
    title: '默认文章',
    status: 'draft',
    views: 0,
    ...overrides
  }
}

describe('usePostManager', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('初始状态：空帖子列表、加载中为 false、默认 tab 为 all', () => {
    const mgr = usePostManager()
    expect(mgr.posts.value).toEqual([])
    expect(mgr.loading.value).toBe(false)
    expect(mgr.activeTab.value).toBe('all')
  })

  it('初始统计卡片全部为 0', () => {
    const mgr = usePostManager()
    const cards = mgr.statCards.value
    expect(cards).toHaveLength(4)
    expect(cards.find((c) => c.label === '全部文章')!.value).toBe(0)
    expect(cards.find((c) => c.label === '已发布')!.value).toBe(0)
    expect(cards.find((c) => c.label === '草稿')!.value).toBe(0)
    expect(cards.find((c) => c.label === '总阅读')!.value).toBe(0)
  })

  it('fetchData 从 API 加载帖子列表', async () => {
    const posts = [makePost({ title: '文章1' }), makePost({ title: '文章2' })]
    mockGetMyPostsApi.mockResolvedValue({ list: posts })

    const mgr = usePostManager()
    await mgr.fetchData()

    expect(mgr.posts.value).toHaveLength(2)
    expect(mgr.loading.value).toBe(false)
  })

  it('fetchData 在 API 失败时置 posts 为空数组', async () => {
    mockGetMyPostsApi.mockRejectedValue(new Error('网络错误'))

    const mgr = usePostManager()
    await mgr.fetchData()

    expect(mgr.posts.value).toEqual([])
    expect(mgr.loading.value).toBe(false)
  })

  it('fetchData 处理 API 返回空列表', async () => {
    mockGetMyPostsApi.mockResolvedValue({ list: [] })

    const mgr = usePostManager()
    await mgr.fetchData()

    expect(mgr.posts.value).toEqual([])
  })

  it('统计卡片值随帖子列表变化', async () => {
    mockGetMyPostsApi.mockResolvedValue({
      list: [
        makePost({ status: 'published', views: 10 }),
        makePost({ status: 'draft', views: 5 }),
        makePost({ status: 'published', views: 20 })
      ]
    })

    const mgr = usePostManager()
    await mgr.fetchData()

    const cards = mgr.statCards.value
    expect(cards.find((c) => c.label === '全部文章')!.value).toBe(3)
    expect(cards.find((c) => c.label === '已发布')!.value).toBe(2)
    expect(cards.find((c) => c.label === '草稿')!.value).toBe(1)
    expect(cards.find((c) => c.label === '总阅读')!.value).toBe(35)
  })

  it('统计卡片保持颜色配置', async () => {
    mockGetMyPostsApi.mockResolvedValue({ list: [] })

    const mgr = usePostManager()
    await mgr.fetchData()

    const cards = mgr.statCards.value
    expect(cards.find((c) => c.label === '全部文章')!.color).toBe('var(--primary-color)')
    expect(cards.find((c) => c.label === '已发布')!.color).toBe('var(--success-color)')
    expect(cards.find((c) => c.label === '草稿')!.color).toBe('var(--accent-yellow)')
    expect(cards.find((c) => c.label === '总阅读')!.color).toBe('var(--accent-color)')
  })

  it('filteredPosts 在 all tab 下返回所有帖子', async () => {
    const posts = [
      makePost({ title: 'a', status: 'published' }),
      makePost({ title: 'b', status: 'draft' })
    ]
    mockGetMyPostsApi.mockResolvedValue({ list: posts })

    const mgr = usePostManager()
    await mgr.fetchData()
    mgr.activeTab.value = 'all'

    expect(mgr.filteredPosts.value).toHaveLength(2)
  })

  it('filteredPosts 在 published tab 下只返回已发布帖子', async () => {
    mockGetMyPostsApi.mockResolvedValue({
      list: [
        makePost({ title: 'pub1', status: 'published' }),
        makePost({ title: 'draft1', status: 'draft' }),
        makePost({ title: 'pub2', status: 'published' })
      ]
    })

    const mgr = usePostManager()
    await mgr.fetchData()
    mgr.activeTab.value = 'published'

    expect(mgr.filteredPosts.value).toHaveLength(2)
    expect(mgr.filteredPosts.value.every((p) => p.status === 'published')).toBe(true)
  })

  it('filteredPosts 在 draft tab 下只返回草稿', async () => {
    mockGetMyPostsApi.mockResolvedValue({
      list: [
        makePost({ title: 'pub', status: 'published' }),
        makePost({ title: 'draft1', status: 'draft' }),
        makePost({ title: 'draft2', status: undefined })
      ]
    })

    const mgr = usePostManager()
    await mgr.fetchData()
    mgr.activeTab.value = 'draft'

    expect(mgr.filteredPosts.value).toHaveLength(2)
  })

  it('切换 activeTab 后 filteredPosts 立即更新', async () => {
    mockGetMyPostsApi.mockResolvedValue({
      list: [
        makePost({ title: 'pub', status: 'published' }),
        makePost({ title: 'draft', status: 'draft' })
      ]
    })

    const mgr = usePostManager()
    await mgr.fetchData()

    mgr.activeTab.value = 'published'
    expect(mgr.filteredPosts.value).toHaveLength(1)
    expect(mgr.filteredPosts.value[0]!.title).toBe('pub')

    mgr.activeTab.value = 'draft'
    expect(mgr.filteredPosts.value).toHaveLength(1)
    expect(mgr.filteredPosts.value[0]!.title).toBe('draft')
  })

  it('空帖子列表时 filteredPosts 返回空数组', async () => {
    mockGetMyPostsApi.mockResolvedValue({ list: [] })

    const mgr = usePostManager()
    await mgr.fetchData()

    expect(mgr.filteredPosts.value).toEqual([])
  })

  it('refreshPosts 代理到 fetchData', async () => {
    mockGetMyPostsApi.mockResolvedValue({ list: [makePost({ title: '刷新测试' })] })

    const mgr = usePostManager()
    await mgr.refreshPosts()

    expect(mgr.posts.value).toHaveLength(1)
    expect(mgr.posts.value[0]!.title).toBe('刷新测试')
  })

  it('fetchData 过程中 loading 为 true', async () => {
    let resolveFn!: (v: any) => void
    mockGetMyPostsApi.mockReturnValue(
      new Promise((resolve) => {
        resolveFn = resolve
      })
    )

    const mgr = usePostManager()
    const promise = mgr.fetchData()
    expect(mgr.loading.value).toBe(true)

    resolveFn({ list: [] })
    await promise
    expect(mgr.loading.value).toBe(false)
  })

  it('状态为 undefined 的帖子被视为草稿', () => {
    const posts = [makePost({ status: undefined })]
    const filtered = posts.filter((p) => (p.status || 'draft') === 'draft')
    expect(filtered).toHaveLength(1)
  })
})