import { describe, it, expect } from 'vitest'
import {
  camelToKebab,
  kebabToCamel,
  capitalize,
  lowercaseFirst,
  truncate,
  maskPhone,
  maskEmail
} from '@/lib/utils/string'

describe('camelToKebab', () => {
  it('驼峰转短横线', () => {
    expect(camelToKebab('helloWorld')).toBe('hello-world')
    expect(camelToKebab('getUserInfo')).toBe('get-user-info')
    expect(camelToKebab('ABC')).toBe('-a-b-c')
  })

  it('空字符串返回空', () => {
    expect(camelToKebab('')).toBe('')
  })
})

describe('kebabToCamel', () => {
  it('短横线转驼峰', () => {
    expect(kebabToCamel('hello-world')).toBe('helloWorld')
    expect(kebabToCamel('get-user-info')).toBe('getUserInfo')
    expect(kebabToCamel('a-b-c')).toBe('aBC')
  })

  it('空字符串返回空', () => {
    expect(kebabToCamel('')).toBe('')
  })
})

describe('capitalize', () => {
  it('首字母大写', () => {
    expect(capitalize('hello')).toBe('Hello')
    expect(capitalize('HELLO')).toBe('HELLO')
    expect(capitalize('h')).toBe('H')
  })

  it('空字符串返回空', () => {
    expect(capitalize('')).toBe('')
  })
})

describe('lowercaseFirst', () => {
  it('首字母小写', () => {
    expect(lowercaseFirst('Hello')).toBe('hello')
    expect(lowercaseFirst('HELLO')).toBe('hELLO')
    expect(lowercaseFirst('H')).toBe('h')
  })

  it('空字符串返回空', () => {
    expect(lowercaseFirst('')).toBe('')
  })
})

describe('truncate', () => {
  it('短字符串不截断', () => {
    expect(truncate('hello', 10)).toBe('hello')
  })

  it('长字符串截断加省略号', () => {
    expect(truncate('hello world this is long', 10)).toBe('hello worl...')
  })

  it('自定义后缀', () => {
    expect(truncate('hello world', 5, '…')).toBe('hello…')
  })

  it('空字符串返回空', () => {
    expect(truncate('', 10)).toBe('')
  })
})

describe('maskPhone', () => {
  it('手机号脱敏', () => {
    expect(maskPhone('13800138000')).toBe('138****8000')
  })

  it('非11位号码原样返回', () => {
    expect(maskPhone('12345')).toBe('12345')
    expect(maskPhone('')).toBe('')
  })
})

describe('maskEmail', () => {
  it('邮箱脱敏', () => {
    expect(maskEmail('test@example.com')).toBe('t***t@example.com')
    expect(maskEmail('abcdef@example.com')).toBe('a***f@example.com')
  })

  it('短用户名不脱敏', () => {
    expect(maskEmail('ab@example.com')).toBe('ab@example.com')
  })

  it('无效邮箱原样返回', () => {
    expect(maskEmail('')).toBe('')
    expect(maskEmail('not-email')).toBe('not-email')
  })
})
