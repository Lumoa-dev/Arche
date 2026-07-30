import { describe, it, expect, vi, beforeEach } from 'vitest'

describe('useArChartTheme', () => {
  beforeEach(() => {
    // 模拟 document 和 CSS 变量
    const style = {
      getPropertyValue: vi.fn((name: string) => {
        const map: Record<string, string> = {
          '--border-color': 'rgba(26,24,23,0.1)',
          '--primary-color': '#b83a2a',
          '--primary-hover-color': '#d44a3a',
          '--bg-color': '#f5f0e8',
          '--bg-inset-color': '#ede5d8',
          '--surface-color': 'rgba(245,240,232,0.88)',
          '--text-primary': 'rgba(26,24,23,0.92)',
          '--text-secondary': 'rgba(26,24,23,0.72)',
          '--text-tertiary': 'rgba(26,24,23,0.54)',
          '--text-disabled': 'rgba(26,24,23,0.34)',
          '--accent-blue': '#4a7c94',
          '--accent-yellow': '#d4a017',
          '--accent-green': '#2d5a3a',
          '--accent-cinnabar': '#c23a2b'
        }
        return { trim: () => map[name] ?? '' }
      })
    } as unknown as CSSStyleDeclaration

    vi.stubGlobal('getComputedStyle', vi.fn(() => style))
  })

  it('tokens 返回所有 token 值', async () => {
    const { useArChartTheme } = await import('@/lib/composables/useArChartTheme')
    const { tokens } = useArChartTheme()

    const t = tokens()
    expect(t.accent).toBe('#b83a2a')
    expect(t.borderLight).toBe('rgba(26,24,23,0.1)')
    expect(t.textPrimary).toBe('rgba(26,24,23,0.92)')
    expect(t.textSecondary).toBe('rgba(26,24,23,0.72)')
  })

  it('palette 返回颜色数组', async () => {
    const { useArChartTheme } = await import('@/lib/composables/useArChartTheme')
    const { palette } = useArChartTheme()

    const colors = palette()
    expect(colors).toHaveLength(5)
    expect(colors[0]).toBe('#b83a2a')
    expect(colors[1]).toBe('#4a7c94')
  })

  it('tooltipStyle 返回正确的样式对象', async () => {
    const { useArChartTheme } = await import('@/lib/composables/useArChartTheme')
    const { tooltipStyle } = useArChartTheme()

    const style = tooltipStyle()
    expect(style.backgroundColor).toBe('rgba(245,240,232,0.88)')
    expect(style.borderWidth).toBe(1)
    expect(style.textStyle.color).toBe('rgba(26,24,23,0.92)')
    expect(style.textStyle.fontSize).toBe(12)
  })

  it('axisStyle 返回正确的样式对象', async () => {
    const { useArChartTheme } = await import('@/lib/composables/useArChartTheme')
    const { axisStyle } = useArChartTheme()

    const style = axisStyle()
    expect(style.axisLine.lineStyle.color).toBe('rgba(26,24,23,0.1)')
    expect(style.axisLabel.color).toBe('rgba(26,24,23,0.54)')
    expect(style.axisLabel.fontSize).toBe(11)
    expect(style.splitLine.show).toBe(false)
  })

  it('textStyle 返回正确的样式', async () => {
    const { useArChartTheme } = await import('@/lib/composables/useArChartTheme')
    const { textStyle } = useArChartTheme()

    const style = textStyle(14)
    expect(style.color).toBe('rgba(26,24,23,0.72)')
    expect(style.fontSize).toBe(14)
  })

  it('textStyle 使用默认字号', async () => {
    const { useArChartTheme } = await import('@/lib/composables/useArChartTheme')
    const { textStyle } = useArChartTheme()

    const style = textStyle()
    expect(style.fontSize).toBe(12)
  })

  it('readCSSVar 使用 fallback 当 CSS 变量未定义', async () => {
    // 覆盖 getComputedStyle 返回空值
    const emptyStyle = {
      getPropertyValue: vi.fn(() => ({ trim: () => '' }))
    } as unknown as CSSStyleDeclaration
    vi.stubGlobal('getComputedStyle', vi.fn(() => emptyStyle))

    const { useArChartTheme } = await import('@/lib/composables/useArChartTheme')
    const { tokens } = useArChartTheme()

    const t = tokens()
    expect(t.accent).toBe('#b83a2a') // 默认 fallback
    expect(t.textPrimary).toBe('rgba(26,24,23,0.92)')
  })
})