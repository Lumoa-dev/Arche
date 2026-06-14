import { describe, it, expect } from 'vitest'
import {
  parseSearchQuery,
  getFilterValue,
  hasIdFilter,
  getSearchText
} from '@/lib/utils/search-parser'

describe('parseSearchQuery', () => {
  it('空输入', () => {
    const result = parseSearchQuery('')
    expect(result.text).toBe('')
    expect(result.filters).toEqual([])
  })

  it('纯文本搜索', () => {
    const result = parseSearchQuery('如何优化性能')
    expect(result.text).toBe('如何优化性能')
    expect(result.filters).toEqual([])
  })

  it('单 filter 搜索', () => {
    const result = parseSearchQuery('type:post')
    expect(result.text).toBe('')
    expect(result.filters).toHaveLength(1)
    expect(result.filters[0]).toEqual({ key: 'type', value: 'post', raw: 'type:post' })
  })

  it('多 filter + 文本', () => {
    const result = parseSearchQuery('type:post status:active 如何优化')
    expect(result.text).toBe('如何优化')
    expect(result.filters).toHaveLength(2)
    expect(result.filters[0]).toEqual({ key: 'type', value: 'post', raw: 'type:post' })
    expect(result.filters[1]).toEqual({ key: 'status', value: 'active', raw: 'status:active' })
  })

  it('is: 关键词', () => {
    const result = parseSearchQuery('is:open')
    expect(result.filters).toHaveLength(1)
    expect(result.filters[0]).toEqual({ key: 'is', value: 'open', raw: 'is:open' })
  })

  it('不认识的 key 不解析为 filter', () => {
    const result = parseSearchQuery('unknown:value hello')
    expect(result.filters).toEqual([])
    expect(result.text).toBe('unknown:value hello')
  })

  it('引号内的空格', () => {
    const result = parseSearchQuery('type:post "hello world"')
    expect(result.text).toBe('hello world')
    expect(result.filters).toHaveLength(1)
  })

  it('key 大小写不敏感', () => {
    const result = parseSearchQuery('Type:post')
    expect(result.filters[0]?.key).toBe('type')
  })
})

describe('getFilterValue', () => {
  it('提取存在的 filter 值', () => {
    const parsed = parseSearchQuery('type:post status:active')
    expect(getFilterValue(parsed, 'type')).toBe('post')
    expect(getFilterValue(parsed, 'status')).toBe('active')
  })

  it('不存在的 filter 返回 undefined', () => {
    const parsed = parseSearchQuery('hello')
    expect(getFilterValue(parsed, 'type')).toBeUndefined()
  })
})

describe('hasIdFilter', () => {
  it('包含 id: 前缀', () => {
    expect(hasIdFilter(parseSearchQuery('id:abc-123'))).toBe(true)
  })

  it('包含 sid: 前缀', () => {
    expect(hasIdFilter(parseSearchQuery('sid:user-xxx'))).toBe(true)
  })

  it('不包含 id filter', () => {
    expect(hasIdFilter(parseSearchQuery('type:post'))).toBe(false)
  })
})

describe('getSearchText', () => {
  it('移除所有 filter 后返回纯文本', () => {
    expect(getSearchText('type:post status:active hello')).toBe('hello')
  })

  it('纯文本原样返回', () => {
    expect(getSearchText('hello world')).toBe('hello world')
  })
})
