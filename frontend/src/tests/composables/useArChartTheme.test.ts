import { describe, it, expect, beforeEach, vi } from 'vitest'
import { useArChartTheme } from '@/lib/composables/useArChartTheme'

describe('useArChartTheme', () => {
  beforeEach(() => {
    // 重置 CSS 变量
    document.documentElement.style.setProperty('--primary-color', '#b83a2a')
    document.documentElement.style.setProperty('--bg-color', '#f5f0e8')
    document.documentElement.style.setProperty('--border-color', 'rgba(26,24,23,0.1)')
    document.documentElement.style.setProperty('--text-primary', 'rgba(26,24,23,0.92)')
    document.documentElement.style.setProperty('--text-secondary', 'rgba(26,24,23,0.72)')
    document.documentElement.style.setProperty('--text-tertiary', 'rgba(26,24,23,0.54)')
    document.documentElement.style.setProperty('--text-disabled', 'rgba(26,24,23,0.34)')
    document.documentElement.style.setProperty('--primary-hover-color', '#d44a3a')
    document.documentElement.style.setProperty('--bg-inset-color', '#ede5d8')
    document.documentElement.style.setProperty('--surface-color', 'rgba(245,240,232,0.88)')
    document.documentElement.style.setProperty('--accent-blue', '#4a7c94')
    document.documentElement.style.setProperty('--accent-yellow', '#d4a017')
    document.documentElement.style.setProperty('--accent-green', '#2d5a3a')
    document.documentElement.style.setProperty('--accent-cinnabar', '#c23a2b')
  })

  it('tokens() 返回所有主题 token', () => {
    const { tokens } = useArChartTheme()
    const t = tokens()

    expect(t.accent).toBe('#b83a2a')
    expect(t.bgMuted).toBe('#f5f0e8')
    expect(t.borderLight).toBe('rgba(26,24,23,0.1)')
    expect(t.textPrimary).toBe('rgba(26,24,23,0.92)')
    expect(t.textSecondary).toBe('rgba(26,24,23,0.72)')
    expect(t.textTertiary).toBe('rgba(26,24,23,0.54)')
    expect(t.textQuaternary).toBe('rgba(26,24,23,0.34)')
    expect(t.accentHover).toBe('#d44a3a')
    expect(t.warmLight).toBe('#ede5d8')
    expect(t.warm).toBe('rgba(245,240,232,0.88)')
  })

  it('tokens() 使用默认值当 CSS 变量未定义', () => {
    // 清除所有 CSS 变量
    const props = [
      '--primary-color', '--bg-color', '--border-color', '--text-primary',
      '--text-secondary', '--text-tertiary', '--text-disabled',
      '--primary-hover-color', '--bg-inset-color', '--surface-color'
    ]
    props.forEach(p => document.documentElement.style.removeProperty(p))

    const { tokens } = useArChartTheme()
    const t = tokens()

    expect(t.accent).toBe('#b83a2a')
    expect(t.bgMuted).toBe('#f5f0e8')
    expect(t.borderLight).toBe('rgba(26,24,23,0.1)')
    expect(t.textPrimary).toBe('rgba(26,24,23,0.92)')
    expect(t.textSecondary).toBe('rgba(26,24,23,0.72)')
    expect(t.textTertiary).toBe('rgba(26,24,23,0.54)')
    expect(t.textQuaternary).toBe('rgba(26,24,23,0.34)')
  })

  it('palette() 返回 5 个颜色', () => {
    const { palette } = useArChartTheme()
    const p = palette()

    expect(p).toHaveLength(5)
    expect(p[0]).toBe('#b83a2a')
    expect(p[1]).toBe('#4a7c94')
    expect(p[2]).toBe('#d4a017')
    expect(p[3]).toBe('#2d5a3a')
    expect(p[4]).toBe('#c23a2b')
  })

  it('tooltipStyle() 返回正确的样式结构', () => {
    const { tooltipStyle } = useArChartTheme()
    const style = tooltipStyle()

    expect(style).toHaveProperty('backgroundColor')
    expect(style).toHaveProperty('borderColor')
    expect(style).toHaveProperty('borderWidth')
    expect(style).toHaveProperty('textStyle')
    expect(style.textStyle).toHaveProperty('color')
    expect(style.textStyle).toHaveProperty('fontSize')
    expect(style.borderWidth).toBe(1)
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

  it('textStyle() 使用默认字号 12', () => {
    const { textStyle } = useArChartTheme()
    const style = textStyle()

    expect(style.fontSize).toBe(12)
    expect(style).toHaveProperty('color')
  })

  it('textStyle() 接受自定义字号', () => {
    const { textStyle } = useArChartTheme()
    const style = textStyle(16)

    expect(style.fontSize).toBe(16)
  })
})