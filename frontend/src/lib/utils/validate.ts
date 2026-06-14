// 表单校验规则工具函数

/**
 * 校验手机号码
 * @param phone 手机号码
 */
export function isPhone(phone: string): boolean {
  const reg = /^1[3-9]\d{9}$/
  return reg.test(phone)
}

/**
 * 校验邮箱地址
 * @param email 邮箱地址
 */
export function isEmail(email: string): boolean {
  const reg = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/
  return reg.test(email)
}

/**
 * 校验身份证号码
 * @param idCard 身份证号码
 */
export function isIdCard(idCard: string): boolean {
  const reg = /(^\d{18}$)|(^\d{17}(\d|X|x)$)/
  if (!reg.test(idCard)) return false

  // 校验码验证
  const weights = [7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2]
  const codes = ['1', '0', 'X', '9', '8', '7', '6', '5', '4', '3', '2']
  let sum = 0

  for (let i = 0; i < 17; i++) {
    const char = idCard.charAt(i)
    const weight = weights[i] || 0
    sum += parseInt(char || '0') * weight
  }

  const code = codes[sum % 11]
  const lastChar = idCard.charAt(17)
  return !!lastChar && code === lastChar.toUpperCase()
}

/**
 * 校验URL地址
 * @param url URL地址
 */
export function isUrl(url: string): boolean {
  const reg = /^https?:\/\/.+/
  return reg.test(url)
}

/**
 * 校验IP地址
 * @param ip IP地址
 */
export function isIp(ip: string): boolean {
  const reg = /^((25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(25[0-5]|2[0-4]\d|[01]?\d\d?)$/
  return reg.test(ip)
}

/**
 * 校验是否是数字
 * @param value 数值
 */
export function isNumber(value: any): boolean {
  return !isNaN(parseFloat(value)) && isFinite(value)
}

/**
 * 校验是否是整数
 * @param value 数值
 */
export function isInteger(value: any): boolean {
  return isNumber(value) && value % 1 === 0
}

/**
 * 校验是否是小数
 * @param value 数值
 */
export function isFloat(value: any): boolean {
  return isNumber(value) && value % 1 !== 0
}

/**
 * 校验是否是中文
 * @param str 字符串
 */
export function isChinese(str: string): boolean {
  const reg = /^[一-龥]+$/
  return reg.test(str)
}

/**
 * 校验是否包含特殊字符
 * @param str 字符串
 */
export function hasSpecialChar(str: string): boolean {
  const reg =
    /[`~!@#$%^&*()_\-+=<>?:"{}|,./;'\\[\]·~！@#￥%……&*（）——\-+={}|《》？：“”【】、；‘’，。、]/im
  return reg.test(str)
}

/**
 * 校验密码强度
 * 密码必须包含大小写字母和数字，长度8-20位
 * @param password 密码
 */
export function validatePasswordStrength(password: string): {
  level: 0 | 1 | 2 | 3 // 0: 弱, 1: 中, 2: 强, 3: 非常强
  valid: boolean
} {
  if (!password) return { level: 0, valid: false }

  let level = 0
  if (password.length >= 8) level++
  if (/[a-z]/.test(password)) level++
  if (/[A-Z]/.test(password)) level++
  if (/[0-9]/.test(password)) level++
  if (
    /[`~!@#$%^&*()_\-+=<>?:"{}|,./;'\\[\]·~！@#￥%……&*（）——\-+={}|《》？：“”【】、；‘’，。、]/.test(
      password
    )
  )
    level++

  return {
    level: Math.min(level, 3) as 0 | 1 | 2 | 3,
    valid: password.length >= 8 && password.length <= 20 && level >= 3
  }
}
