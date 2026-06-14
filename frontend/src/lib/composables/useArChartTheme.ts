/**
 * ECharts 图表主题 composable
 *
 * 从 CSS 变量读取主题色值，提供统一的图表配色方案。
 * 自动适配 light / dark 主题。
 */

export interface ChartTokens {
  borderLight: string
  accent: string
  accentHover: string
  bgMuted: string
  warmLight: string
  warm: string
  textPrimary: string
  textSecondary: string
  textTertiary: string
  textQuaternary: string
}

function readCSSVar(name: string, fallback: string): string {
  if (typeof document === 'undefined') return fallback
  const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim()
  return value || fallback
}

export function useArChartTheme() {
  function tokens(): ChartTokens {
    return {
      borderLight: readCSSVar('--border-color', 'rgba(26,24,23,0.1)'),
      accent: readCSSVar('--primary-color', '#b83a2a'),
      accentHover: readCSSVar('--primary-hover-color', '#d44a3a'),
      bgMuted: readCSSVar('--bg-color', '#f5f0e8'),
      warmLight: readCSSVar('--bg-inset-color', '#ede5d8'),
      warm: readCSSVar('--surface-color', 'rgba(245,240,232,0.88)'),
      textPrimary: readCSSVar('--text-primary', 'rgba(26,24,23,0.92)'),
      textSecondary: readCSSVar('--text-secondary', 'rgba(26,24,23,0.72)'),
      textTertiary: readCSSVar('--text-tertiary', 'rgba(26,24,23,0.54)'),
      textQuaternary: readCSSVar('--text-disabled', 'rgba(26,24,23,0.34)')
    }
  }

  function palette(): string[] {
    return [
      readCSSVar('--primary-color', '#b83a2a'),
      readCSSVar('--accent-blue', '#4a7c94'),
      readCSSVar('--accent-yellow', '#d4a017'),
      readCSSVar('--accent-green', '#2d5a3a'),
      readCSSVar('--accent-cinnabar', '#c23a2b')
    ]
  }

  function tooltipStyle() {
    const t = tokens()
    return {
      backgroundColor: readCSSVar('--surface-color', 'rgba(245,240,232,0.88)'),
      borderColor: readCSSVar('--border-color', 'rgba(26,24,23,0.1)'),
      borderWidth: 1,
      textStyle: {
        color: t.textPrimary,
        fontSize: 12
      }
    }
  }

  function axisStyle() {
    const t = tokens()
    return {
      axisLine: { lineStyle: { color: t.borderLight } },
      axisTick: { lineStyle: { color: t.borderLight } },
      axisLabel: { color: t.textTertiary, fontSize: 11 },
      splitLine: { show: false }
    }
  }

  function textStyle(fontSize = 12) {
    const t = tokens()
    return {
      color: t.textSecondary,
      fontSize
    }
  }

  return { tokens, palette, tooltipStyle, axisStyle, textStyle }
}
