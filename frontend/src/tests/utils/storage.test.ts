import { describe, it, expect, beforeEach } from 'vitest'
import { localStorageUtil, sessionStorageUtil } from '@/lib/utils/storage'

// 每个测试前清除存储
beforeEach(() => {
  window.localStorage.clear()
  window.sessionStorage.clear()
})

describe('localStorageUtil', () => {
  it('set / get 基本存取', () => {
    localStorageUtil.set('key1', 'value1')
    expect(localStorageUtil.get('key1')).toBe('value1')
  })

  it('存取对象', () => {
    const obj = { a: 1, b: [2, 3] }
    localStorageUtil.set('obj', obj)
    expect(localStorageUtil.get('obj')).toEqual(obj)
  })

  it('不存在的 key 返回默认值', () => {
    expect(localStorageUtil.get('nonexistent')).toBeNull()
    expect(localStorageUtil.get('nonexistent', 'default')).toBe('default')
  })

  it('undefined / null 不写入', () => {
    localStorageUtil.set('undef', undefined)
    expect(localStorageUtil.get('undef')).toBeNull()

    localStorageUtil.set('nil', null)
    expect(localStorageUtil.get('nil')).toBeNull()
  })

  it('remove 删除指定 key', () => {
    localStorageUtil.set('key', 'val')
    localStorageUtil.remove('key')
    expect(localStorageUtil.get('key')).toBeNull()
  })

  it('clear 清空所有', () => {
    localStorageUtil.set('a', '1')
    localStorageUtil.set('b', '2')
    localStorageUtil.clear()
    expect(localStorageUtil.get('a')).toBeNull()
    expect(localStorageUtil.get('b')).toBeNull()
  })

  it('keys 返回所有键', () => {
    localStorageUtil.set('x', '1')
    localStorageUtil.set('y', '2')
    const keys = localStorageUtil.keys()
    expect(keys).toContain('x')
    expect(keys).toContain('y')
  })
})

describe('sessionStorageUtil', () => {
  it('set / get 基本存取', () => {
    sessionStorageUtil.set('key', 'value')
    expect(sessionStorageUtil.get('key')).toBe('value')
  })

  it('不存在的 key 返回 null', () => {
    expect(sessionStorageUtil.get('nothing')).toBeNull()
  })

  it('clear 和 session 隔离', () => {
    sessionStorageUtil.set('sess', 'data')
    localStorageUtil.set('local', 'data')
    sessionStorageUtil.clear()
    // session 清空不影响 localStorage
    expect(sessionStorageUtil.get('sess')).toBeNull()
    expect(localStorageUtil.get('local')).toBe('data')
  })
})
