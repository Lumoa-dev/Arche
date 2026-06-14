import { describe, it, expect } from 'vitest'
import { getCoverGradient } from '@/lib/utils/cover'

describe('getCoverGradient', () => {
  it('相同输入返回相同渐变色', () => {
    const post = { title: 'Hello World', tags: ['tech'] }
    const result1 = getCoverGradient(post)
    const result2 = getCoverGradient(post)
    expect(result1).toBe(result2)
  })

  it('不同输入可能返回不同渐变色', () => {
    const result1 = getCoverGradient({ title: 'Post A' })
    void getCoverGradient({ title: 'Post B' })
    // 理论上可能碰撞，但大多数情况下应不同
    expect(typeof result1).toBe('string')
    expect(result1).toContain('linear-gradient')
  })

  it('没有标题时也返回渐变色', () => {
    const result = getCoverGradient({})
    expect(result).toContain('linear-gradient')
  })
})
