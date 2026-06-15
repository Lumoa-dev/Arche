/**
 * search store 集成测试。
 *
 * 测什么：真实的 Pinia Store + Mock API → Store 状态联动
 * Mock 边界：@/services/api/search（API 层）
 * 不 mock：store 本身、search-parser
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useSearchStore } from '@/lib/store/modules/search'

// ── Mock API 层 ──
const { mockGetSuggestions } = vi.hoisted(() => ({
  mockGetSuggestions: vi.fn()
}))

vi.mock('@/services/api/search', () => ({
  getSearchSuggestionsApi: mockGetSuggestions
}))

describe('search store 集成测试', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  describe('setKeyword + fetchSuggestions', () => {
    it('输入关键词后触发 API 请求（防抖）', async () => {
      const searchStore = useSearchStore()

      // 模拟 API 返回建议
      mockGetSuggestions.mockResolvedValue({
        code: 'ok',
        data: {
          items: [{ type: 'post', sid: '1', label: '测试文章', sublabel: '技术', url: '/posts/1' }]
        }
      })

      searchStore.setKeyword('测试')

      // 防抖 300ms，此时 API 还未调用
      expect(mockGetSuggestions).not.toHaveBeenCalled()
      expect(searchStore.loading).toBe(true)

      // 快进 300ms
      await vi.advanceTimersByTimeAsync(300)

      // API 被调用
      expect(mockGetSuggestions).toHaveBeenCalledWith('测试', 5)

      // 验证 store 状态更新
      expect(searchStore.suggestions).toHaveLength(1)
      expect(searchStore.suggestions[0]!.label).toBe('测试文章')
      expect(searchStore.loading).toBe(false)
      expect(searchStore.active).toBe(true)
    })

    it('空关键词不清除时不触发 API', () => {
      const searchStore = useSearchStore()
      searchStore.setKeyword('')

      expect(mockGetSuggestions).not.toHaveBeenCalled()
      expect(searchStore.suggestions).toEqual([])
      expect(searchStore.loading).toBe(false)
    })

    it('连续输入只触发最后一次 API', async () => {
      const searchStore = useSearchStore()
      mockGetSuggestions.mockResolvedValue({ code: 'ok', data: { items: [] } })

      searchStore.setKeyword('a')
      searchStore.setKeyword('ab')
      searchStore.setKeyword('abc')

      await vi.advanceTimersByTimeAsync(300)

      // 只调用了一次
      expect(mockGetSuggestions).toHaveBeenCalledTimes(1)
      expect(mockGetSuggestions).toHaveBeenCalledWith('abc', 5)
    })

    it('API 失败时设置 error 并清空建议', async () => {
      const searchStore = useSearchStore()
      mockGetSuggestions.mockRejectedValue(new Error('网络错误'))

      searchStore.setKeyword('搜索')
      await vi.advanceTimersByTimeAsync(300)

      expect(searchStore.error).toBe('搜索建议请求失败')
      expect(searchStore.suggestions).toEqual([])
      expect(searchStore.loading).toBe(false)
    })

    it('API 返回空建议时仍正确响应', async () => {
      const searchStore = useSearchStore()
      mockGetSuggestions.mockResolvedValue({ code: 'ok', data: { items: [] } })

      searchStore.setKeyword('nothing')
      await vi.advanceTimersByTimeAsync(300)

      expect(searchStore.suggestions).toEqual([])
      expect(searchStore.hasSuggestions).toBe(false)
      expect(searchStore.error).toBeNull()
    })
  })

  describe('clearSearch', () => {
    it('清除搜索后重置所有状态', () => {
      const searchStore = useSearchStore()
      searchStore.keyword = 'test'
      searchStore.suggestions = [
        { type: 'post', sid: '1', label: 'Test', sublabel: '', url: '/test' }
      ]
      searchStore.loading = true
      searchStore.active = true

      searchStore.clearSearch()

      expect(searchStore.keyword).toBe('')
      expect(searchStore.suggestions).toEqual([])
      expect(searchStore.loading).toBe(false)
      expect(searchStore.active).toBe(false)
      expect(searchStore.error).toBeNull()
    })
  })

  describe('fetchSuggestions（直接调用）', () => {
    it('直接调用 fetchSuggestions 获取建议', async () => {
      const searchStore = useSearchStore()
      mockGetSuggestions.mockResolvedValue({
        code: 'ok',
        data: {
          items: [{ type: 'tag', sid: 't1', label: 'Vue.js', sublabel: '框架', url: '/tags/vue' }]
        }
      })

      await searchStore.fetchSuggestions('Vue')

      expect(mockGetSuggestions).toHaveBeenCalledWith('Vue', 5)
      expect(searchStore.suggestions).toHaveLength(1)
      expect(searchStore.suggestions[0]!.label).toBe('Vue.js')
    })
  })
})
