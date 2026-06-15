import { describe, it, expect } from 'vitest'
import {
  isPhone,
  isEmail,
  isIdCard,
  isUrl,
  isIp,
  isNumber,
  isInteger,
  isFloat,
  isChinese,
  hasSpecialChar,
  validatePasswordStrength
} from '@/lib/utils/validate'

describe('isPhone', () => {
  it('有效的手机号码', () => {
    expect(isPhone('13800138000')).toBe(true)
    expect(isPhone('15912345678')).toBe(true)
    expect(isPhone('18888888888')).toBe(true)
  })

  it('无效的手机号码', () => {
    expect(isPhone('12345678901')).toBe(false) // 不以1开头
    expect(isPhone('1380013800')).toBe(false) // 少一位
    expect(isPhone('138001380000')).toBe(false) // 多一位
    expect(isPhone('')).toBe(false)
    expect(isPhone('abc')).toBe(false)
  })
})

describe('isEmail', () => {
  it('有效的邮箱地址', () => {
    expect(isEmail('test@example.com')).toBe(true)
    expect(isEmail('user.name+tag@example.co.uk')).toBe(true)
    expect(isEmail('a@b.cd')).toBe(true)
  })

  it('无效的邮箱地址', () => {
    expect(isEmail('')).toBe(false)
    expect(isEmail('not-email')).toBe(false)
    expect(isEmail('@example.com')).toBe(false)
    expect(isEmail('user@')).toBe(false)
    expect(isEmail('user@.com')).toBe(false)
  })
})

describe('isIdCard', () => {
  it('有效的身份证号码', () => {
    // 使用校验码正确的测试号
    expect(isIdCard('11010519491231002X')).toBe(true)
  })

  it('无效的身份证号码', () => {
    expect(isIdCard('')).toBe(false)
    expect(isIdCard('12345')).toBe(false)
    expect(isIdCard('12345678901234567890')).toBe(false)
  })
})

describe('isUrl', () => {
  it('有效的 URL', () => {
    expect(isUrl('https://example.com')).toBe(true)
    expect(isUrl('http://example.com/path')).toBe(true)
    expect(isUrl('https://sub.example.com/path/to/page?q=1')).toBe(true)
  })

  it('无效的 URL', () => {
    expect(isUrl('')).toBe(false)
    expect(isUrl('not-a-url')).toBe(false)
    expect(isUrl('ftp://example.com')).toBe(false)
  })
})

describe('isIp', () => {
  it('有效的 IP 地址', () => {
    expect(isIp('192.168.1.1')).toBe(true)
    expect(isIp('8.8.8.8')).toBe(true)
    expect(isIp('255.255.255.255')).toBe(true)
    expect(isIp('0.0.0.0')).toBe(true)
  })

  it('无效的 IP 地址', () => {
    expect(isIp('')).toBe(false)
    expect(isIp('256.1.2.3')).toBe(false)
    expect(isIp('1.2.3')).toBe(false)
    expect(isIp('abc.def.ghi.jkl')).toBe(false)
  })
})

describe('isNumber', () => {
  it('有效的数字', () => {
    expect(isNumber(123)).toBe(true)
    expect(isNumber('123')).toBe(true)
    expect(isNumber(3.14)).toBe(true)
    expect(isNumber('3.14')).toBe(true)
    expect(isNumber(0)).toBe(true)
    expect(isNumber(-1)).toBe(true)
  })

  it('无效的数字', () => {
    expect(isNumber('')).toBe(false)
    expect(isNumber('abc')).toBe(false)
    expect(isNumber(undefined)).toBe(false)
    expect(isNumber(NaN)).toBe(false)
  })
})

describe('isInteger', () => {
  it('有效的整数', () => {
    expect(isInteger(42)).toBe(true)
    expect(isInteger('42')).toBe(true)
    expect(isInteger(0)).toBe(true)
    expect(isInteger(-5)).toBe(true)
  })

  it('非整数', () => {
    expect(isInteger(3.14)).toBe(false)
    expect(isInteger('abc')).toBe(false)
  })
})

describe('isFloat', () => {
  it('有效的小数', () => {
    expect(isFloat(3.14)).toBe(true)
    expect(isFloat('3.14')).toBe(true)
    expect(isFloat(0.5)).toBe(true)
  })

  it('非小数', () => {
    expect(isFloat(42)).toBe(false)
    expect(isFloat('abc')).toBe(false)
  })
})

describe('isChinese', () => {
  it('纯中文字符', () => {
    expect(isChinese('中文')).toBe(true)
    expect(isChinese('你好世界')).toBe(true)
  })

  it('非纯中文', () => {
    expect(isChinese('')).toBe(false)
    expect(isChinese('中文123')).toBe(false)
    expect(isChinese('hello')).toBe(false)
    expect(isChinese('中文hello')).toBe(false)
  })
})

describe('hasSpecialChar', () => {
  it('包含特殊字符', () => {
    expect(hasSpecialChar('hello!')).toBe(true)
    expect(hasSpecialChar('test@test')).toBe(true)
    expect(hasSpecialChar('pass#word')).toBe(true)
  })

  it('不包含特殊字符', () => {
    expect(hasSpecialChar('')).toBe(false)
    expect(hasSpecialChar('hello123')).toBe(false)
    expect(hasSpecialChar('你好')).toBe(false)
  })
})

describe('validatePasswordStrength', () => {
  it('空密码返回 level 0', () => {
    const result = validatePasswordStrength('')
    expect(result.level).toBe(0)
    expect(result.valid).toBe(false)
  })

  it('纯数字短密码为弱', () => {
    const result = validatePasswordStrength('123456')
    expect(result.level).toBe(1)
    expect(result.valid).toBe(false)
  })

  it('8位数字密码为中', () => {
    const result = validatePasswordStrength('12345678')
    expect(result.level).toBe(2)
    expect(result.valid).toBe(false)
  })

  it('大小写+数字8位为强', () => {
    const result = validatePasswordStrength('Abc12345')
    expect(result.level).toBe(3)
    expect(result.valid).toBe(true)
  })

  it('大小写+数字+特殊字符为非常强', () => {
    const result = validatePasswordStrength('Abc12345!')
    expect(result.level).toBe(3) // level capped at 3
    expect(result.valid).toBe(true)
  })
})
