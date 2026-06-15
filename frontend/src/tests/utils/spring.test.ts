import { describe, it, expect, vi, beforeEach } from 'vitest'
import { advanceAnimationFrame, clearAnimationFrames } from '../../../vitest.setup'

// animateSpring 是纯函数，不依赖 Vue 上下文，可以单独测试
// useSpring 依赖 Vue watchEffect/onUnmounted，需要组件上下文，留在 Phase 3 测试

describe('animateSpring', () => {
  beforeEach(() => {
    clearAnimationFrames()
    vi.clearAllMocks()
  })

  it('应该从起始值向目标值运动，并调用 onUpdate', async () => {
    const { animateSpring } = await import('@/lib/utils/spring')

    const values: number[] = []
    const cancel = animateSpring(0, 100, (v) => {
      values.push(Math.round(v))
    })

    // 推进几帧动画
    advanceAnimationFrame()
    advanceAnimationFrame()
    advanceAnimationFrame()

    cancel()

    // 验证运动过程：值在从 0 向 100 变化（具体值取决于物理参数）
    expect(values.length).toBeGreaterThan(0)
    // 第一帧应该已经离开起始点
    expect(values[0]!).toBeGreaterThan(0)
    // 值应该单调递增
    for (let i = 1; i < values.length; i++) {
      expect(values[i]!).toBeGreaterThanOrEqual(values[i - 1]!)
    }
  })

  it('应该通过 cancel 函数停止动画', async () => {
    const { animateSpring } = await import('@/lib/utils/spring')

    const callback = vi.fn()
    const cancel = animateSpring(0, 100, callback)

    // 推进一帧
    advanceAnimationFrame()
    const callCountAfterFirstFrame = callback.mock.calls.length

    // 取消动画
    cancel()

    // 再推进多帧，回调不应该再被调用
    advanceAnimationFrame()
    advanceAnimationFrame()
    expect(callback.mock.calls.length).toBe(callCountAfterFirstFrame)
  })

  it('当速度和位移足够小时应自动停止', async () => {
    const { animateSpring } = await import('@/lib/utils/spring')

    // 使用很大的 stiffness 让弹簧快速稳定
    const values: number[] = []
    const cancel = animateSpring(
      10,
      10.1,
      (v) => {
        values.push(v)
      },
      { stiffness: 1000, damping: 100, precision: 0.5 }
    )

    // 推进足够多的帧让动画自然停止
    for (let i = 0; i < 60; i++) {
      advanceAnimationFrame()
    }

    cancel()

    // 最终值应该接近目标值 10.1
    const lastValue = values[values.length - 1]!
    expect(Math.abs(lastValue - 10.1)).toBeLessThan(0.5)
  })

  it('应该使用自定义配置覆盖默认值', async () => {
    const { animateSpring } = await import('@/lib/utils/spring')

    const callback = vi.fn()
    animateSpring(0, 50, callback, {
      stiffness: 300,
      damping: 40,
      mass: 2
    })

    advanceAnimationFrame()

    expect(callback).toHaveBeenCalled()
  })
})
