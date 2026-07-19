/**
 * useArChartTheme 测试
 *
 * 测试 ECharts 图表主题 composable 的色值读取和样式生成。
 * jsdom 环境下 getComputedStyle 返回空值，所以会使用 fallback 值。
 */

import { describe, it, expect } from 'vitest'

describe('useArChartTheme', () => {
  it('tokens 返回默认值（jsdom 无 CSS 变量）', async () => {
    const { useArChartTheme } = await import('@/lib/composables/useArChartTheme')
    const { tokens } = useArChartTheme()
    const result = tokens()
    expect(result.borderLight).toBe('rgba(26,24,23,0.1)')
    expect(result.accent).toBe('#b83a2a')
    expect(result.accentHover).toBe('#d44a3a')
    expect(result.bgMuted).toBe('#f5f0e8')
    expect(result.warmLight).toBe('#ede5d8')
    expect(result.warm).toBe('rgba(245,240,232,0.88)')
    expect(result.textPrimary).toBe('rgba(26,24,23,0.92)')
    expect(result.textSecondary).toBe('rgba(26,24,23,0.72)')
    expect(result.textTertiary).toBe('rgba(26,24,23,0.54)')
    expect(result.textQuaternary).toBe('rgba(26,24,23,0.34)')
  })

  it('palette 返回默认色板', async () => {
    const { useArChartTheme } = await import('@/lib/composables/useArChartTheme')
    const { palette } = useArChartTheme()
    const result = palette()
    expect(result).toHaveLength(5)
    expect(result[0]).toBe('#b83a2a')
    expect(result[1]).toBe('#4a7c94')
    expect(result[2]).toBe('#d4a017')
    expect(result[3]).toBe('#2d5a3a')
    expect(result[4]).toBe('#c23a2b')
  })

  it('tooltipStyle 返回默认样式', async () => {
    const { useArChartTheme } = await import('@/lib/composables/useArChartTheme')
    const { tooltipStyle } = useArChartTheme()
    const result = tooltipStyle()
    expect(result.backgroundColor).toBe('rgba(245,240,232,0.88)')
    expect(result.borderColor).toBe('rgba(26,24,23,0.1)')
    expect(result.borderWidth).toBe(1)
    expect(result.textStyle.color).toBe('rgba(26,24,23,0.92)')
    expect(result.textStyle.fontSize).toBe(12)
  })

  it('axisStyle 返回默认样式', async () => {
    const { useArChartTheme } = await import('@/lib/composables/useArChartTheme')
    const { axisStyle } = useArChartTheme()
    const result = axisStyle()
    expect(result.axisLine.lineStyle.color).toBe('rgba(26,24,23,0.1)')
    expect(result.axisTick.lineStyle.color).toBe('rgba(26,24,23,0.1)')
    expect(result.axisLabel.color).toBe('rgba(26,24,23,0.54)')
    expect(result.axisLabel.fontSize).toBe(11)
    expect(result.splitLine.show).toBe(false)
  })

  it('textStyle 返回默认样式', async () => {
    const { useArChartTheme } = await import('@/lib/composables/useArChartTheme')
    const { textStyle } = useArChartTheme()
    const result = textStyle(14)
    expect(result.color).toBe('rgba(26,24,23,0.72)')
    expect(result.fontSize).toBe(14)
  })

  it('textStyle 默认字体大小', async () => {
    const { useArChartTheme } = await import('@/lib/composables/useArChartTheme')
    const { textStyle } = useArChartTheme()
    const result = textStyle()
    expect(result.fontSize).toBe(12)
  })

  it('多次调用 tokens 返回一致结果', async () => {
    const { useArChartTheme } = await import('@/lib/composables/useArChartTheme')
    const { tokens } = useArChartTheme()
    const first = tokens()
    const second = tokens()
    expect(first).toEqual(second)
  })
})