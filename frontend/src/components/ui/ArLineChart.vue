<script setup lang="ts">
import { computed } from 'vue'
import { useArChartTheme } from '@/composables/useArChartTheme'
import ArChart from './ArChart.vue'

const props = withDefaults(
  defineProps<{
    /** X 轴标签 */
    categories?: string[]
    /** 数据系列 */
    series?: { name: string; data: number[] }[]
    /** 显示面积渐变瀑布 */
    showArea?: boolean
    /** 显示峰值基准线 */
    showMarkLine?: boolean
    /** 是否平滑（贝塞尔） */
    smooth?: boolean
    /** 图表高度 */
    height?: number
  }>(),
  {
    categories: () => [],
    series: () => [],
    showArea: true,
    showMarkLine: false,
    smooth: true,
    height: 300
  }
)

const { tokens, palette, textStyle, axisStyle, tooltipStyle } = useArChartTheme()

const option = computed(() => {
  const t = tokens()
  const axis = axisStyle()
  return {
    color: palette(),
    tooltip: {
      ...tooltipStyle(),
      trigger: 'axis',
    },
    grid: {
      left: 40,
      right: 16,
      top: 16,
      bottom: 24,
    },
    xAxis: {
      type: 'category',
      data: props.categories,
      boundaryGap: false,
      ...axis,
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: t.borderLight } },
      ...axis,
    },
    series: props.series.map((s) => {
      const serie: Record<string, unknown> = {
        type: 'line',
        name: s.name,
        data: s.data,
        smooth: props.smooth,
        symbol: 'none',
        lineStyle: { width: 1.5, color: t.accent },
        itemStyle: { color: t.accent },
      }
      if (props.showArea) {
        serie.areaStyle = {
          color: {
            type: 'linear',
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: t.accent + '60' },
              { offset: 1, color: t.accent + '05' },
            ],
          },
        }
      }
      if (props.showMarkLine) {
        const values = s.data.filter((v) => v != null) as number[]
        const max = Math.max(...values)
        serie.markLine = {
          silent: true,
          data: [
            {
              type: 'max',
              label: {
                formatter: '峰值: {c}',
                ...textStyle(11),
                color: t.textSecondary,
              },
              lineStyle: { color: t.textQuaternary, type: 'dashed' as const, width: 1 },
            },
          ],
        }
      }
      return serie
    }),
  } as Record<string, unknown>
})
</script>

<template>
  <ArChart :option="option" :height="height" />
</template>
