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
    // 所有合法号段第二位
    expect(isPhone('13000000000')).toBe(true)
    expect(isPhone('15000000000')).toBe(true)
    expect(isPhone('17000000000')).toBe(true)
    expect(isPhone('19000000000')).toBe(true)
  })

  it('无效的手机号码', () => {
    expect(isPhone('12345678901')).toBe(false) // 不以1开头
    expect(isPhone('1380013800')).toBe(false) // 少一位
    expect(isPhone('138001380000')).toBe(false) // 多一位
    expect(isPhone('')).toBe(false)
    expect(isPhone('abc')).toBe(false)
    expect(isPhone('12000000000')).toBe(false) // 第二位为2（不在3-9范围）
    expect(isPhone('11000000000')).toBe(false) // 第二位为1
    expect(isPhone('10000000000')).toBe(false) // 第二位为0
  })
})

describe('isEmail', () => {
  it('有效的邮箱地址', () => {
    expect(isEmail('test@example.com')).toBe(true)
    expect(isEmail('user.name+tag@example.co.uk')).toBe(true)
    expect(isEmail('a@b.cd')).toBe(true)
    expect(isEmail('user_name@example.com')).toBe(true)
    expect(isEmail('user%tag@example.com')).toBe(true)
  })

  it('无效的邮箱地址', () => {
    expect(isEmail('')).toBe(false)
    expect(isEmail('not-email')).toBe(false)
    expect(isEmail('@example.com')).toBe(false)
    expect(isEmail('user@')).toBe(false)
    expect(isEmail('user@.com')).toBe(false)
    expect(isEmail('user@com')).toBe(false) // 缺少顶级域
    expect(isEmail('user@example.c')).toBe(false) // 顶级域太短
  })
})

describe('isIdCard', () => {
  it('有效的身份证号码', () => {
    // 使用校验码正确的测试号
    expect(isIdCard('11010519491231002X')).toBe(true)
  })

  it('有效的身份证号码含小写x', () => {
    expect(isIdCard('11010519491231002x')).toBe(true) // 小写x也是有效的
  })

  it('无效的身份证号码', () => {
    expect(isIdCard('')).toBe(false)
    expect(isIdCard('12345')).toBe(false)
    expect(isIdCard('12345678901234567890')).toBe(false)
  })

  it('校验码错误', () => {
    expect(isIdCard('110105194912310021')).toBe(false) // 校验码应为X
    expect(isIdCard('110105194912310022')).toBe(false)
  })
})

describe('isUrl', () => {
  it('有效的 URL', () => {
    expect(isUrl('https://example.com')).toBe(true)
    expect(isUrl('http://example.com/path')).toBe(true)
    expect(isUrl('https://sub.example.com/path/to/page?q=1')).toBe(true)
    expect(isUrl('http://localhost:8080')).toBe(true)
    expect(isUrl('https://example.com/path#fragment')).toBe(true)
    expect(isUrl('http://example.com/path?q=1&w=2')).toBe(true)
  })

  it('无效的 URL', () => {
    expect(isUrl('')).toBe(false)
    expect(isUrl('not-a-url')).toBe(false)
    expect(isUrl('ftp://example.com')).toBe(false)
    expect(isUrl('https://')).toBe(false)
    expect(isUrl('http://')).toBe(false)
  })
})

describe('isIp', () => {
  it('有效的 IP 地址', () => {
    expect(isIp('192.168.1.1')).toBe(true)
    expect(isIp('8.8.8.8')).toBe(true)
    expect(isIp('255.255.255.255')).toBe(true)
    expect(isIp('0.0.0.0')).toBe(true)
    expect(isIp('1.2.3.4')).toBe(true)
    expect(isIp('10.0.0.1')).toBe(true)
    expect(isIp('172.16.0.1')).toBe(true)
  })

  it('无效的 IP 地址', () => {
    expect(isIp('')).toBe(false)
    expect(isIp('256.1.2.3')).toBe(false)
    expect(isIp('1.2.3')).toBe(false)
    expect(isIp('abc.def.ghi.jkl')).toBe(false)
    expect(isIp('1.2.3.4.5')).toBe(false)
    expect(isIp('-1.2.3.4')).toBe(false)
    expect(isIp('1.2.3.')).toBe(false)
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
    expect(isNumber(Infinity)).toBe(false) // 无穷大不是有限数
    expect(isNumber(-Infinity)).toBe(false)
  })

  it('无效的数字', () => {
    expect(isNumber('')).toBe(false)
    expect(isNumber('abc')).toBe(false)
    expect(isNumber(undefined)).toBe(false)
    expect(isNumber(NaN)).toBe(false)
    expect(isNumber(null)).toBe(false)
  })
})

describe('isInteger', () => {
  it('有效的整数', () => {
    expect(isInteger(42)).toBe(true)
    expect(isInteger('42')).toBe(true)
    expect(isInteger(0)).toBe(true)
    expect(isInteger(-5)).toBe(true)
    expect(isInteger('0')).toBe(true)
  })

  it('非整数', () => {
    expect(isInteger(3.14)).toBe(false)
    expect(isInteger('abc')).toBe(false)
    expect(isInteger('3.14')).toBe(false)
    expect(isInteger(NaN)).toBe(false)
  })
})

describe('isFloat', () => {
  it('有效的小数', () => {
    expect(isFloat(3.14)).toBe(true)
    expect(isFloat('3.14')).toBe(true)
    expect(isFloat(0.5)).toBe(true)
    expect(isFloat('0.5')).toBe(true)
    expect(isFloat(-1.5)).toBe(true)
  })

  it('非小数', () => {
    expect(isFloat(42)).toBe(false)
    expect(isFloat('abc')).toBe(false)
    expect(isFloat(0)).toBe(false)
    expect(isFloat(NaN)).toBe(false)
  })
})

describe('isChinese', () => {
  it('纯中文字符', () => {
    expect(isChinese('中文')).toBe(true)
    expect(isChinese('你好世界')).toBe(true)
    expect(isChinese('一')).toBe(true)
  })

  it('非纯中文', () => {
    expect(isChinese('')).toBe(false)
    expect(isChinese('中文123')).toBe(false)
    expect(isChinese('hello')).toBe(false)
    expect(isChinese('中文hello')).toBe(false)
    expect(isChinese(' ')).toBe(false)
  })
})

describe('hasSpecialChar', () => {
  it('包含特殊字符', () => {
    expect(hasSpecialChar('hello!')).toBe(true)
    expect(hasSpecialChar('test@test')).toBe(true)
    expect(hasSpecialChar('pass#word')).toBe(true)
    expect(hasSpecialChar('hello world')).toBe(false) // 空格不是特殊字符
    expect(hasSpecialChar('test*test')).toBe(true)
    expect(hasSpecialChar('测试!')).toBe(true)
  })

  it('不包含特殊字符', () => {
    expect(hasSpecialChar('')).toBe(false)
    expect(hasSpecialChar('hello123')).toBe(false)
    expect(hasSpecialChar('你好')).toBe(false)
    expect(hasSpecialChar('abc123ABC')).toBe(false)
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

  it('仅小写字母密码为弱', () => {
    const result = validatePasswordStrength('abcdefgh')
    expect(result.level).toBe(2) // 长度>=8 + 小写 = 2
    expect(result.valid).toBe(false)
  })

  it('仅大写字母密码为弱', () => {
    const result = validatePasswordStrength('ABCDEFGH')
    expect(result.level).toBe(2) // 长度>=8 + 大写 = 2
    expect(result.valid).toBe(false)
  })

  it('超长密码（>20位）无效', () => {
    const result = validatePasswordStrength('Abc12345' + 'x'.repeat(20))
    expect(result.valid).toBe(false)
  })

  it('刚好8位且包含大小写数字为有效', () => {
    const result = validatePasswordStrength('Aa1' + 'b'.repeat(5))
    expect(result.level).toBe(3) // 长度>=8 + 小写 + 大写 + 数字 = 3
    expect(result.valid).toBe(true)
  })
})
