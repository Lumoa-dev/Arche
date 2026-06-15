/**
 * 搜索 Store —— 全局搜索状态管理。
 *
 * 搜索栏的 keyword 通过此 Store 同步到各个页面组件。
 * 页面组件通过 watch(store.keyword) 实现实时过滤。
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { ParsedQuery } from '@/lib/utils/search-parser'
import { parseSearchQuery } from '@/lib/utils/search-parser'
import { getSearchSuggestionsApi } from '@/components/logic/api/search'
import type { SuggestionItem } from '@/components/logic/api/search'

export interface Suggestion {
  type: string
  sid: string
  label: string
  sublabel: string
  url: string
}

export const useSearchStore = defineStore('search', () => {
  // ── 状态 ──
  const keyword = ref('')
  const suggestions = ref<Suggestion[]>([])
  const loading = ref(false)
  const active = ref(false) // 搜索栏是否激活（有焦点或有内容）
  const error = ref<string | null>(null)

  // ── 计算属性 ──
  const parsed = computed<ParsedQuery>(() => parseSearchQuery(keyword.value))

  const hasContent = computed(() => keyword.value.trim().length > 0)

  const hasSuggestions = computed(() => suggestions.value.length > 0)

  // ── 方法 ──
  let debounceTimer: ReturnType<typeof setTimeout> | null = null

  /**
   * 设置搜索关键词，自动解析并触发后端建议请求（防抖 300ms）。
   */
  function setKeyword(text: string) {
    keyword.value = text
    active.value = text.length > 0

    // 清除之前的定时器
    if (debounceTimer !== null) {
      clearTimeout(debounceTimer)
    }

    // 空关键词不请求
    if (!text.trim()) {
      suggestions.value = []
      loading.value = false
      return
    }

    // 防抖 300ms 后请求建议
    loading.value = true
    debounceTimer = setTimeout(async () => {
      try {
        await fetchSuggestions(text)
      } catch (e) {
        console.error('搜索建议请求失败:', e)
        error.value = '搜索建议请求失败'
        suggestions.value = []
      } finally {
        loading.value = false
      }
    }, 300)
  }

  /**
   * 请求后端搜索建议。
   */
  async function fetchSuggestions(q: string) {
    try {
      const response = await getSearchSuggestionsApi(q, 5)
      const data = response as { code?: string; data?: { items?: SuggestionItem[] } }
      suggestions.value = (data?.data?.items ?? []) as Suggestion[]
      error.value = null
    } catch (e) {
      console.error('搜索建议请求失败:', e)
      error.value = '搜索建议请求失败'
      suggestions.value = []
    }
  }

  /**
   * 清除搜索。
   */
  function clearSearch() {
    keyword.value = ''
    suggestions.value = []
    loading.value = false
    active.value = false
    error.value = null
  }

  /**
   * 激活搜索栏（获得焦点）。
   */
  function activate() {
    active.value = true
  }

  /**
   * 停用搜索栏（失去焦点）。
   */
  function deactivate() {
    // 延迟停用以允许点击下拉建议
    setTimeout(() => {
      if (!keyword.value.trim()) {
        active.value = false
      }
    }, 200)
  }

  return {
    keyword,
    suggestions,
    loading,
    active,
    error,
    parsed,
    hasContent,
    hasSuggestions,
    setKeyword,
    clearSearch,
    fetchSuggestions,
    activate,
    deactivate
  }
})
