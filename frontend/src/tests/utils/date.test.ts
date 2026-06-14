import { describe, it, expect } from 'vitest'
import { formatDate, isToday } from '@/lib/utils/date'

describe('formatDate', () => {
  it('Date 对象格式化', () => {
    const d = new Date(2024, 0, 15, 14, 30, 45)
    expect(formatDate(d)).toBe('2024-01-15 14:30:45')
  })

  it('时间戳格式化', () => {
    const ts = new Date(2024, 5, 1, 9, 5, 3).getTime()
    expect(formatDate(ts)).toBe('2024-06-01 09:05:03')
  })

  it('日期字符串格式化', () => {
    expect(formatDate('2024-12-25T10:00:00', 'YYYY-MM-DD')).toBe('2024-12-25')
  })

  it('自定义格式', () => {
    const d = new Date(2024, 0, 1, 8, 0, 0)
    expect(formatDate(d, 'YYYY/MM/DD HH:mm')).toBe('2024/01/01 08:00')
    expect(formatDate(d, 'HH:mm:ss')).toBe('08:00:00')
  })

  it('无效日期返回空字符串', () => {
    expect(formatDate(null as unknown as Date)).toBe('')
    expect(formatDate('invalid-date')).toBe('')
    expect(formatDate(new Date('invalid'))).toBe('')
  })
})

describe('isToday', () => {
  it('今天返回 true', () => {
    expect(isToday(new Date())).toBe(true)
  })

  it('非今天返回 false', () => {
    const yesterday = new Date()
    yesterday.setDate(yesterday.getDate() - 1)
    expect(isToday(yesterday)).toBe(false)
  })

  it('不同月份的同一天返回 false', () => {
    const today = new Date()
    const otherMonth = new Date(today)
    otherMonth.setMonth(today.getMonth() === 0 ? 11 : today.getMonth() - 1)
    expect(isToday(otherMonth)).toBe(false)
  })

  it('不同年份的同一天返回 false', () => {
    const today = new Date()
    const otherYear = new Date(today)
    otherYear.setFullYear(today.getFullYear() - 1)
    expect(isToday(otherYear)).toBe(false)
  })
})

describe('formatRelativeTime', () => {
  it('无效日期返回空字符串', async () => {
    const { formatRelativeTime } = await import('@/utils/date')
    expect(formatRelativeTime(null as unknown as Date)).toBe('')
    expect(formatRelativeTime('invalid')).toBe('')
    expect(formatRelativeTime(new Date('invalid'))).toBe('')
  })

  it('刚刚（小于1分钟）', async () => {
    const { formatRelativeTime } = await import('@/utils/date')
    const now = new Date()
    expect(formatRelativeTime(now)).toBe('刚刚')
  })

  it('分钟前', async () => {
    const { formatRelativeTime } = await import('@/utils/date')
    const fiveMinAgo = new Date(Date.now() - 5 * 60 * 1000)
    expect(formatRelativeTime(fiveMinAgo)).toBe('5分钟前')
  })

  it('小时前', async () => {
    const { formatRelativeTime } = await import('@/utils/date')
    const threeHoursAgo = new Date(Date.now() - 3 * 60 * 60 * 1000)
    expect(formatRelativeTime(threeHoursAgo)).toBe('3小时前')
  })

  it('天前', async () => {
    const { formatRelativeTime } = await import('@/utils/date')
    const twoDaysAgo = new Date(Date.now() - 2 * 24 * 60 * 60 * 1000)
    expect(formatRelativeTime(twoDaysAgo)).toBe('2天前')
  })

  it('周前', async () => {
    const { formatRelativeTime } = await import('@/utils/date')
    const twoWeeksAgo = new Date(Date.now() - 14 * 24 * 60 * 60 * 1000)
    expect(formatRelativeTime(twoWeeksAgo)).toBe('2周前')
  })

  it('个月前', async () => {
    const { formatRelativeTime } = await import('@/utils/date')
    const threeMonthsAgo = new Date(Date.now() - 90 * 24 * 60 * 60 * 1000)
    expect(formatRelativeTime(threeMonthsAgo)).toBe('3个月前')
  })

  it('年前', async () => {
    const { formatRelativeTime } = await import('@/utils/date')
    const twoYearsAgo = new Date(Date.now() - 2 * 365 * 24 * 60 * 60 * 1000)
    expect(formatRelativeTime(twoYearsAgo)).toBe('2年前')
  })
})

describe('getTodayStart', () => {
  it('返回今天 00:00:00.000', async () => {
    const { getTodayStart } = await import('@/utils/date')
    const result = getTodayStart()
    const now = new Date()
    expect(result.getFullYear()).toBe(now.getFullYear())
    expect(result.getMonth()).toBe(now.getMonth())
    expect(result.getDate()).toBe(now.getDate())
    expect(result.getHours()).toBe(0)
    expect(result.getMinutes()).toBe(0)
    expect(result.getSeconds()).toBe(0)
    expect(result.getMilliseconds()).toBe(0)
  })
})

describe('getTodayEnd', () => {
  it('返回今天 23:59:59.999', async () => {
    const { getTodayEnd } = await import('@/utils/date')
    const result = getTodayEnd()
    const now = new Date()
    expect(result.getFullYear()).toBe(now.getFullYear())
    expect(result.getMonth()).toBe(now.getMonth())
    expect(result.getDate()).toBe(now.getDate())
    expect(result.getHours()).toBe(23)
    expect(result.getMinutes()).toBe(59)
    expect(result.getSeconds()).toBe(59)
    expect(result.getMilliseconds()).toBe(999)
  })
})
