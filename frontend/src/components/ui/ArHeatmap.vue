<script setup lang="ts">
import { computed } from 'vue'
import { useArChartTheme } from '@/composables/useArChartTheme'
import ArChart from './ArChart.vue'

const props = withDefaults(
  defineProps<{
    /** [x, y, value] 数据 */
    data?: [number, number, number][]
    /** X 轴标签 */
    categoriesX?: string[]
    /** Y 轴标签 */
    categoriesY?: string[]
    height?: number
  }>(),
  {
    data: () => [],
    categoriesX: () => [],
    categoriesY: () => [],
    height: 300
  }
)

const { tokens, palette, axisStyle, tooltipStyle } = useArChartTheme()

const option = computed(() => {
  const t = tokens()
  const axis = axisStyle()
  return {
    tooltip: {
      ...tooltipStyle(),
      formatter: (p: { value: number[] }) =>
        `${props.categoriesX[p.value[0]]} ~ ${props.categoriesY[p.value[1]]}: ${p.value[2]}`,
    },
    grid: { left: 60, right: 40, top: 16, bottom: 40 },
    xAxis: { type: 'category', data: props.categoriesX, splitArea: { show: true }, ...axis },
    yAxis: { type: 'category', data: props.categoriesY, splitArea: { show: true }, ...axis },
    visualMap: {
      min: 0,
      max: Math.max(...props.data.map((d) => d[2]), 1),
      calculable: true,
      orient: 'horizontal',
      left: 'center',
      bottom: 0,
      inRange: { color: [t.bgMuted, t.warmLight, t.warm, t.accent] },
    },
    series: [
      {
        type: 'heatmap',
        data: props.data,
        label: { show: props.categoriesX.length <= 10 },
        emphasis: {
          itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0,0,0,0.15)' },
        },
      },
    ],
  } as Record<string, unknown>
})
</script>

<template>
  <ArChart :option="option" :height="height" />
</template>
