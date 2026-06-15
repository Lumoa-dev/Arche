import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useSearchStore } from '@/lib/store/modules/search'
import type { SuggestionItem } from '@/components/logic/api/search'

// 模拟搜索建议 API
vi.mock('@/services/api/search', () => ({
  getSearchSuggestionsApi: vi.fn()
}))

import { getSearchSuggestionsApi } from '@/components/logic/api/search'

describe('useSearchStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  describe('初始状态', () => {
    it('keyword 默认为空字符串', () => {
      const store = useSearchStore()
      expect(store.keyword).toBe('')
    })

    it('suggestions 默认为空数组', () => {
      const store = useSearchStore()
      expect(store.suggestions).toEqual([])
    })

    it('loading 默认为 false', () => {
      const store = useSearchStore()
      expect(store.loading).toBe(false)
    })

    it('active 默认为 false', () => {
      const store = useSearchStore()
      expect(store.active).toBe(false)
    })

    it('error 默认为 null', () => {
      const store = useSearchStore()
      expect(store.error).toBeNull()
    })
  })

  describe('计算属性', () => {
    it('parsed 解析纯文本', () => {
      const store = useSearchStore()
      store.keyword = '如何优化'
      expect(store.parsed.text).toBe('如何优化')
      expect(store.parsed.filters).toEqual([])
    })

    it('parsed 解析 key:value 筛选语法', () => {
      const store = useSearchStore()
      store.keyword = 'type:post status:active'
      expect(store.parsed.text).toBe('')
      expect(store.parsed.filters).toEqual([
        { key: 'type', value: 'post', raw: 'type:post' },
        { key: 'status', value: 'active', raw: 'status:active' }
      ])
    })

    it('parsed 混合文本和筛选', () => {
      const store = useSearchStore()
      store.keyword = 'type:post 如何优化'
      expect(store.parsed.text).toBe('如何优化')
      expect(store.parsed.filters).toHaveLength(1)
      expect(store.parsed.filters[0]).toEqual({ key: 'type', value: 'post', raw: 'type:post' })
    })

    it('hasContent 有内容时返回 true', () => {
      const store = useSearchStore()
      store.keyword = 'test'
      expect(store.hasContent).toBe(true)
    })

    it('hasContent 无内容时返回 false', () => {
      const store = useSearchStore()
      expect(store.hasContent).toBe(false)
    })

    it('hasSuggestions 有建议时返回 true', () => {
      const store = useSearchStore()
      store.suggestions = [{ type: 'post', sid: '1', label: 'test', sublabel: '', url: '/post/1' }]
      expect(store.hasSuggestions).toBe(true)
    })

    it('hasSuggestions 无建议时返回 false', () => {
      const store = useSearchStore()
      expect(store.hasSuggestions).toBe(false)
    })
  })

  describe('setKeyword', () => {
    it('设置关键词并激活搜索栏', () => {
      const store = useSearchStore()
      store.setKeyword('测试')
      expect(store.keyword).toBe('测试')
      expect(store.active).toBe(true)
    })

    it('空字符串时清除建议并取消激活', () => {
      const store = useSearchStore()
      store.suggestions = [{ type: 'post', sid: '1', label: 'x', sublabel: '', url: '/x' }]
      store.setKeyword('')
      expect(store.keyword).toBe('')
      expect(store.suggestions).toEqual([])
      expect(store.active).toBe(false)
      expect(store.loading).toBe(false)
    })

    it('设置关键词后 loading 为 true 并触发 300ms 防抖', () => {
      const store = useSearchStore()
      store.setKeyword('test')
      expect(store.loading).toBe(true)

      // 防抖期间再次设置关键词，重新计时
      store.setKeyword('test2')
      vi.advanceTimersByTime(200)
      // 还没到 300ms，loading 仍为 true
      expect(store.loading).toBe(true)
    })

    it('防抖结束后调用 fetchSuggestions', async () => {
      const mockItems = [
        { type: 'post', sid: '1', label: 'Test Post', sublabel: '摘要', url: '/post/1' }
      ]
      vi.mocked(getSearchSuggestionsApi).mockResolvedValueOnce({
        code: '0',
        data: { items: mockItems as SuggestionItem[] }
      })

      const store = useSearchStore()
      store.setKeyword('test')
      vi.advanceTimersByTime(300)
      // 等待异步任务完成
      await vi.waitFor(() => {
        expect(store.loading).toBe(false)
        expect(store.suggestions).toHaveLength(1)
        expect(store.suggestions[0]!.label).toBe('Test Post')
      })
    })

    it('防抖结束后 API 失败时设置 error', async () => {
      vi.mocked(getSearchSuggestionsApi).mockRejectedValueOnce(new Error('Network error'))

      const store = useSearchStore()
      store.setKeyword('test')
      vi.advanceTimersByTime(300)
      await vi.waitFor(() => {
        expect(store.error).toBe('搜索建议请求失败')
        expect(store.loading).toBe(false)
        expect(store.suggestions).toEqual([])
      })
    })
  })

  describe('clearSearch', () => {
    it('清除所有搜索状态', () => {
      const store = useSearchStore()
      store.keyword = 'test'
      store.suggestions = [{ type: 'post', sid: '1', label: 'x', sublabel: '', url: '/x' }]
      store.loading = true
      store.active = true
      store.error = 'some error'

      store.clearSearch()

      expect(store.keyword).toBe('')
      expect(store.suggestions).toEqual([])
      expect(store.loading).toBe(false)
      expect(store.active).toBe(false)
      expect(store.error).toBeNull()
    })
  })

  describe('activate / deactivate', () => {
    it('activate 设置 active 为 true', () => {
      const store = useSearchStore()
      store.activate()
      expect(store.active).toBe(true)
    })

    it('deactivate 在关键词为空时延迟停用', () => {
      const store = useSearchStore()
      store.active = true
      store.deactivate()
      // 200ms 内 active 仍为 true
      expect(store.active).toBe(true)
      vi.advanceTimersByTime(200)
      expect(store.active).toBe(false)
    })

    it('deactivate 有关键词时不停用', () => {
      const store = useSearchStore()
      store.keyword = 'test'
      store.active = true
      store.deactivate()
      vi.advanceTimersByTime(200)
      expect(store.active).toBe(true)
    })
  })

  describe('fetchSuggestions', () => {
    it('成功获取建议', async () => {
      const mockItems = [
        { type: 'post', sid: '1', label: 'Post 1', sublabel: '摘要', url: '/post/1' },
        { type: 'user', sid: 'u1', label: 'User 1', sublabel: '@user1', url: '/user/u1' }
      ]
      vi.mocked(getSearchSuggestionsApi).mockResolvedValueOnce({
        code: '0',
        data: { items: mockItems as SuggestionItem[] }
      })

      const store = useSearchStore()
      await store.fetchSuggestions('test')

      expect(getSearchSuggestionsApi).toHaveBeenCalledWith('test', 5)
      expect(store.suggestions).toHaveLength(2)
      expect(store.error).toBeNull()
    })

    it('API 失败时设置 error', async () => {
      vi.mocked(getSearchSuggestionsApi).mockRejectedValueOnce(new Error('Network error'))

      const store = useSearchStore()
      await store.fetchSuggestions('test')

      expect(store.error).toBe('搜索建议请求失败')
      expect(store.suggestions).toEqual([])
    })
  })
})
