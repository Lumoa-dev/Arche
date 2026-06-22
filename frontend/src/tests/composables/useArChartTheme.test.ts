/**
 * useArChartTheme 测试
 *
 * 测试图表主题 composable 的 token 读取、调色板、工具提示/坐标轴样式。
 */

import { describe, expect, it, beforeEach, afterEach } from 'vitest'
import { useArChartTheme } from '../../lib/composables/useArChartTheme'

describe('useArChartTheme', () => {
  const originalGetComputedStyle = window.getComputedStyle

  beforeEach(() => {
    // 为 document.documentElement 设置模拟 CSS 变量
    document.documentElement.style.setProperty('--primary-color', '#ff6600')
    document.documentElement.style.setProperty('--primary-hover-color', '#ff8844')
    document.documentElement.style.setProperty('--border-color', 'rgba(0,0,0,0.2)')
    document.documentElement.style.setProperty('--bg-color', '#ffffff')
    document.documentElement.style.setProperty('--text-primary', '#1a1a1a')
    document.documentElement.style.setProperty('--text-secondary', '#4a4a4a')
    document.documentElement.style.setProperty('--text-disabled', '#cccccc')
  })

  afterEach(() => {
    // 恢复 getComputedStyle
    window.getComputedStyle = originalGetComputedStyle
  })

  it('tokens() 返回所有主题 Token', () => {
    const { tokens } = useArChartTheme()
    const t = tokens()

    expect(t.accent).toBe('#ff6600')
    expect(t.accentHover).toBe('#ff8844')
    expect(t.borderLight).toBe('rgba(0,0,0,0.2)')
    expect(t.bgMuted).toBe('#ffffff')
    expect(t.textPrimary).toBe('#1a1a1a')
    expect(t.textSecondary).toBe('#4a4a4a')
    expect(t.textQuaternary).toBe('#cccccc')
  })

  it('tokens() 在 CSS 变量缺失时使用默认值', () => {
    // 清除 CSS 变量
    document.documentElement.style.removeProperty('--primary-color')
    document.documentElement.style.removeProperty('--border-color')

    const { tokens } = useArChartTheme()
    const t = tokens()

    expect(t.accent).toBe('#b83a2a')
    expect(t.borderLight).toBe('rgba(26,24,23,0.1)')
  })

  it('readCSSVar 在无 document 时返回回退值', () => {
    // 模拟 SSR 环境（document 为 undefined）
    const docRef = (globalThis as any).document
    ;(globalThis as any).document = undefined

    const { tokens } = useArChartTheme()
    const t = tokens()

    expect(t.accent).toBe('#b83a2a')
    expect(t.textPrimary).toBe('rgba(26,24,23,0.92)')

    // 恢复 document
    ;(globalThis as any).document = docRef
  })

  it('palette() 返回 5 色调色板', () => {
    const { palette } = useArChartTheme()
    const p = palette()

    expect(p).toHaveLength(5)
    expect(p[0]).toBe('#ff6600')
  })

  it('palette() 在 CSS 变量缺失时使用回退值', () => {
    document.documentElement.style.removeProperty('--primary-color')

    const { palette } = useArChartTheme()
    const p = palette()

    expect(p[0]).toBe('#b83a2a')
  })

  it('tooltipStyle() 返回正确的 tooltip 样式对象', () => {
    const { tooltipStyle } = useArChartTheme()
    const style = tooltipStyle()

    expect(style).toHaveProperty('backgroundColor')
    expect(style).toHaveProperty('borderColor')
    expect(style).toHaveProperty('borderWidth', 1)
    expect(style).toHaveProperty('textStyle')
    expect(style.textStyle).toHaveProperty('color')
    expect(style.textStyle).toHaveProperty('fontSize', 12)
  })

  it('axisStyle() 返回正确的坐标轴样式对象', () => {
    const { axisStyle } = useArChartTheme()
    const style = axisStyle()

    expect(style).toHaveProperty('axisLine')
    expect(style).toHaveProperty('axisTick')
    expect(style).toHaveProperty('axisLabel')
    expect(style).toHaveProperty('splitLine')
    expect(style.splitLine).toEqual({ show: false })
  })

  it('textStyle() 返回正确的文字样式', () => {
    const { textStyle } = useArChartTheme()
    const s12 = textStyle()
    const s16 = textStyle(16)

    expect(s12).toHaveProperty('fontSize', 12)
    expect(s16).toHaveProperty('fontSize', 16)
    expect(s12.color).toBe('#4a4a4a')
  })
})