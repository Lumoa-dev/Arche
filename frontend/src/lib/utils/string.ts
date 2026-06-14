// 字符串处理工具函数

/**
 * 驼峰命名转短横线命名
 * @param str 驼峰字符串
 */
export function camelToKebab(str: string): string {
  return str.replace(/([a-z0-9]|(?=[A-Z]))([A-Z])/g, '$1-$2').toLowerCase()
}

/**
 * 短横线命名转驼峰命名
 * @param str 短横线字符串
 */
export function kebabToCamel(str: string): string {
  return str.replace(/-(\w)/g, (_, c) => c.toUpperCase())
}

/**
 * 首字母大写
 * @param str 字符串
 */
export function capitalize(str: string): string {
  if (!str) return ''
  return str.charAt(0).toUpperCase() + str.slice(1)
}

/**
 * 首字母小写
 * @param str 字符串
 */
export function lowercaseFirst(str: string): string {
  if (!str) return ''
  return str.charAt(0).toLowerCase() + str.slice(1)
}

/**
 * 截断字符串，超出部分用省略号显示
 * @param str 字符串
 * @param length 最大长度
 * @param suffix 后缀，默认是...
 */
export function truncate(str: string, length: number, suffix = '...'): string {
  if (!str) return ''
  if (str.length <= length) return str
  return str.slice(0, length) + suffix
}

/**
 * 生成随机字符串
 * @param length 字符串长度
 */
export function randomString(length: number): string {
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
  let result = ''
  for (let i = 0; i < length; i++) {
    result += chars.charAt(Math.floor(Math.random() * chars.length))
  }
  return result
}

/**
 * 手机号码脱敏
 * @param phone 手机号码
 */
export function maskPhone(phone: string): string {
  if (!phone || phone.length !== 11) return phone
  return phone.replace(/(\d{3})\d{4}(\d{4})/, '$1****$2')
}

/**
 * 邮箱脱敏
 * @param email 邮箱地址
 */
export function maskEmail(email: string): string {
  if (!email || !email.includes('@')) return email
  const parts = email.split('@')
  const username = parts[0]
  const domain = parts[1]
  if (!username || !domain || username.length <= 2) return email
  return `${username.charAt(0)}***${username.charAt(username.length - 1)}@${domain}`
}
