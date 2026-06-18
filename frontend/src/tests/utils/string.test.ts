import { describe, it, expect } from 'vitest'
import {
  camelToKebab,
  kebabToCamel,
  capitalize,
  lowercaseFirst,
  truncate,
  maskPhone,
  maskEmail,
  randomString,
  htmlToText
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
    expect(maskEmail('a@example.com')).toBe('a@example.com')
  })

  it('无效邮箱原样返回', () => {
    expect(maskEmail('')).toBe('')
    expect(maskEmail('not-email')).toBe('not-email')
  })
})

describe('randomString', () => {
  it('生成指定长度的字符串', () => {
    expect(randomString(0)).toBe('')
    expect(randomString(8).length).toBe(8)
    expect(randomString(32).length).toBe(32)
    expect(randomString(128).length).toBe(128)
  })

  it('结果只包含字母和数字', () => {
    const str = randomString(1000)
    expect(str).toMatch(/^[A-Za-z0-9]+$/)
  })

  it('多次调用应产生不同结果', () => {
    const result1 = randomString(20)
    const result2 = randomString(20)
    expect(result1).not.toBe(result2)
  })
})

describe('htmlToText', () => {
  it('基本 HTML 标签剥离', () => {
    expect(htmlToText('<p>Hello World</p>')).toBe('Hello World')
  })

  it('嵌套标签', () => {
    expect(htmlToText('<div><p>Hello <b>World</b></p></div>')).toBe('Hello World')
  })

  it('空字符串返回空', () => {
    expect(htmlToText('')).toBe('')
  })

  it('纯文本原样返回', () => {
    expect(htmlToText('just text')).toBe('just text')
  })

  it('script 标签内容被移除', () => {
    expect(htmlToText('<script>alert("xss")</script><p>content</p>')).toBe('content')
  })

  it('style 标签内容被移除', () => {
    expect(htmlToText('<style>.cls{color:red}</style><p>text</p>')).toBe('text')
  })

  it('换行和多余空格处理', () => {
    const result = htmlToText('<p>line1</p><p>line2</p>')
    // 不同标签间的文本可能连在一起
    expect(result).toContain('line1')
    expect(result).toContain('line2')
  })
})
