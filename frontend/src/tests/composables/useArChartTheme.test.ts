import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useArChartTheme } from '@/lib/composables/useArChartTheme'

describe('useArChartTheme', () => {
  beforeEach(() => {
    // 模拟 CSS 变量
    document.documentElement.style.setProperty('--primary-color', '#b83a2a')
    document.documentElement.style.setProperty('--primary-hover-color', '#d44a3a')
    document.documentElement.style.setProperty('--bg-color', '#f5f0e8')
    document.documentElement.style.setProperty('--bg-inset-color', '#ede5d8')
    document.documentElement.style.setProperty('--surface-color', 'rgba(245,240,232,0.88)')
    document.documentElement.style.setProperty('--border-color', 'rgba(26,24,23,0.1)')
    document.documentElement.style.setProperty('--text-primary', 'rgba(26,24,23,0.92)')
    document.documentElement.style.setProperty('--text-secondary', 'rgba(26,24,23,0.72)')
    document.documentElement.style.setProperty('--text-tertiary', 'rgba(26,24,23,0.54)')
    document.documentElement.style.setProperty('--text-disabled', 'rgba(26,24,23,0.34)')
    document.documentElement.style.setProperty('--accent-blue', '#4a7c94')
    document.documentElement.style.setProperty('--accent-yellow', '#d4a017')
    document.documentElement.style.setProperty('--accent-green', '#2d5a3a')
    document.documentElement.style.setProperty('--accent-cinnabar', '#c23a2b')
  })

  it('tokens() 返回所有主题令牌', () => {
    const { tokens } = useArChartTheme()
    const t = tokens()

    expect(t.accent).toBe('#b83a2a')
    expect(t.accentHover).toBe('#d44a3a')
    expect(t.bgMuted).toBe('#f5f0e8')
    expect(t.warmLight).toBe('#ede5d8')
    expect(t.warm).toBe('rgba(245,240,232,0.88)')
    expect(t.borderLight).toBe('rgba(26,24,23,0.1)')
    expect(t.textPrimary).toBe('rgba(26,24,23,0.92)')
    expect(t.textSecondary).toBe('rgba(26,24,23,0.72)')
    expect(t.textTertiary).toBe('rgba(26,24,23,0.54)')
    expect(t.textQuaternary).toBe('rgba(26,24,23,0.34)')
  })

  it('tokens() 在 CSS 变量缺失时使用 fallback 值', () => {
    // 清除所有 CSS 变量
    document.documentElement.getPropertyValue = () => ''
    // 使用 getComputedStyle 模拟
    const origGetComputedStyle = globalThis.getComputedStyle
    globalThis.getComputedStyle = vi.fn().mockReturnValue({
      getPropertyValue: () => ''
    })

    const { tokens } = useArChartTheme()
    const t = tokens()

    expect(t.accent).toBe('#b83a2a')
    expect(t.borderLight).toBe('rgba(26,24,23,0.1)')

    globalThis.getComputedStyle = origGetComputedStyle
  })

  it('palette() 返回 5 个颜色值', () => {
    const { palette } = useArChartTheme()
    const colors = palette()

    expect(colors).toHaveLength(5)
    expect(colors[0]).toBe('#b83a2a')
    expect(colors[1]).toBe('#4a7c94')
    expect(colors[2]).toBe('#d4a017')
    expect(colors[3]).toBe('#2d5a3a')
    expect(colors[4]).toBe('#c23a2b')
  })

  it('tooltipStyle() 返回正确的样式结构', () => {
    const { tooltipStyle } = useArChartTheme()
    const style = tooltipStyle()

    expect(style).toHaveProperty('backgroundColor')
    expect(style).toHaveProperty('borderColor')
    expect(style).toHaveProperty('borderWidth')
    expect(style).toHaveProperty('textStyle')
    expect(style.textStyle).toHaveProperty('fontSize')
    expect(style.textStyle.fontSize).toBe(12)
  })

  it('axisStyle() 返回正确的样式结构', () => {
    const { axisStyle } = useArChartTheme()
    const style = axisStyle()

    expect(style).toHaveProperty('axisLine')
    expect(style).toHaveProperty('axisTick')
    expect(style).toHaveProperty('axisLabel')
    expect(style).toHaveProperty('splitLine')
    expect(style.splitLine.show).toBe(false)
  })

  it('textStyle() 使用默认字体大小', () => {
    const { textStyle } = useArChartTheme()
    const style = textStyle()

    expect(style).toHaveProperty('fontSize')
    expect(style.fontSize).toBe(12)
  })

  it('textStyle() 接受自定义字体大小', () => {
    const { textStyle } = useArChartTheme()
    const style = textStyle(16)

    expect(style.fontSize).toBe(16)
  })
})