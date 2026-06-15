// 日期处理工具函数

/**
 * 格式化日期
 * @param date 日期对象或时间戳
 * @param format 格式化字符串，支持YYYY-MM-DD HH:mm:ss等
 */
export function formatDate(date: Date | number | string, format = 'YYYY-MM-DD HH:mm:ss'): string {
  if (!date) {
    return ''
  }
  const d = new Date(date)
  if (isNaN(d.getTime())) {
    return ''
  }

  const year = d.getFullYear().toString()
  const month = (d.getMonth() + 1).toString().padStart(2, '0')
  const day = d.getDate().toString().padStart(2, '0')
  const hour = d.getHours().toString().padStart(2, '0')
  const minute = d.getMinutes().toString().padStart(2, '0')
  const second = d.getSeconds().toString().padStart(2, '0')

  return format
    .replace('YYYY', year)
    .replace('MM', month)
    .replace('DD', day)
    .replace('HH', hour)
    .replace('mm', minute)
    .replace('ss', second)
}

/**
 * 格式化相对时间
 * @param date 日期对象或时间戳
 */
export function formatRelativeTime(date: Date | number | string): string {
  if (!date) {
    return ''
  }
  const d = new Date(date)
  if (isNaN(d.getTime())) {
    return ''
  }

  const now = new Date()
  const diff = now.getTime() - d.getTime()

  const minute = 60 * 1000
  const hour = 60 * minute
  const day = 24 * hour
  const week = 7 * day
  const month = 30 * day
  const year = 365 * day

  if (diff < minute) {
    return '刚刚'
  } else if (diff < hour) {
    return `${Math.floor(diff / minute)}分钟前`
  } else if (diff < day) {
    return `${Math.floor(diff / hour)}小时前`
  } else if (diff < week) {
    return `${Math.floor(diff / day)}天前`
  } else if (diff < month) {
    return `${Math.floor(diff / week)}周前`
  } else if (diff < year) {
    return `${Math.floor(diff / month)}个月前`
  } else {
    return `${Math.floor(diff / year)}年前`
  }
}

/**
 * 获取今天的开始时间
 */
export function getTodayStart(): Date {
  const date = new Date()
  date.setHours(0, 0, 0, 0)
  return date
}

/**
 * 获取今天的结束时间
 */
export function getTodayEnd(): Date {
  const date = new Date()
  date.setHours(23, 59, 59, 999)
  return date
}

/**
 * 判断是否是今天
 * @param date 日期
 */
export function isToday(date: Date | number | string): boolean {
  const d = new Date(date)
  const today = new Date()
  return (
    d.getFullYear() === today.getFullYear() &&
    d.getMonth() === today.getMonth() &&
    d.getDate() === today.getDate()
  )
}
