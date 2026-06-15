import { describe, it, expect, vi, beforeEach } from 'vitest'

vi.mock('@/lib/services/request', () => ({
  get: vi.fn()
}))

beforeEach(() => {
  vi.clearAllMocks()
})

describe('search API', () => {
  it('getSearchSuggestionsApi 发送正确 URL 和查询参数', async () => {
    const { getSearchSuggestionsApi } = await import('@/lib/services/api/search')
    const { get } = await import('@/lib/services/request')
    vi.mocked(get).mockResolvedValue({
      code: '200',
      data: { items: [] }
    })

    await getSearchSuggestionsApi('hello', 5)
    expect(get).toHaveBeenCalledWith('/search/suggestions', { q: 'hello', limit: 5 }, undefined)
  })

  it('getSearchSuggestionsApi 使用默认 limit = 5', async () => {
    const { getSearchSuggestionsApi } = await import('@/lib/services/api/search')
    const { get } = await import('@/lib/services/request')
    vi.mocked(get).mockResolvedValue({
      code: '200',
      data: { items: [] }
    })

    await getSearchSuggestionsApi('test')
    expect(get).toHaveBeenCalledWith('/search/suggestions', { q: 'test', limit: 5 }, undefined)
  })

  it('getSearchSuggestionsApi 正确解析建议列表', async () => {
    const { getSearchSuggestionsApi } = await import('@/lib/services/api/search')
    const { get } = await import('@/lib/services/request')
    const mockItems = [
      { type: 'post', sid: '1', label: '文章1', sublabel: '描述1', url: '/blog/post-1' }
    ]
    vi.mocked(get).mockResolvedValue({
      code: '200',
      data: { items: mockItems }
    })

    const result = await getSearchSuggestionsApi('文章')
    expect(result.data.items).toHaveLength(1)
    expect(result.data.items[0]!.label).toBe('文章1')
    expect(result.data.items[0]!.url).toBe('/blog/post-1')
  })
})
