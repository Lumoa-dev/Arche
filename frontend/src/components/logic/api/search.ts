import { get, type RequestConfig } from '../request'

export interface SuggestionItem {
  type: string
  sid: string
  label: string
  sublabel: string
  url: string
}

export interface SearchSuggestionsResponse {
  code: string
  data: {
    items: SuggestionItem[]
  }
}

export const getSearchSuggestionsApi = (q: string, limit: number = 5, config?: RequestConfig) =>
  get<SearchSuggestionsResponse>('/search/suggestions', { q, limit }, config)
