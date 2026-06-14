<script setup lang="ts">
import { computed } from 'vue'
import { useArChartTheme } from '@/lib/composables/useArChartTheme'
import ArChart from './ArChart.vue'

const props = withDefaults(
  defineProps<{
    categories?: string[]
    series?: { name: string; data: number[] }[]
    height?: number
    /** 柱状图方向 */
    layout?: 'vertical' | 'horizontal'
  }>(),
  {
    categories: () => [],
    series: () => [],
    height: 300,
    layout: 'vertical'
  }
)

const { tokens, palette, axisStyle, tooltipStyle } = useArChartTheme()

const option = computed(() => {
  const t = tokens()
  const axis = axisStyle()
  const isHorizontal = props.layout === 'horizontal'

  return {
    color: palette(),
    tooltip: {
      ...tooltipStyle(),
      trigger: 'axis',
      axisPointer: { type: 'shadow' }
    },
    grid: {
      left: isHorizontal ? 60 : 40,
      right: 16,
      top: 16,
      bottom: 24
    },
    xAxis: isHorizontal
      ? { type: 'value', splitLine: { lineStyle: { color: t.borderLight } }, ...axis }
      : { type: 'category', data: props.categories, ...axis },
    yAxis: isHorizontal
      ? { type: 'category', data: props.categories, ...axis }
      : { type: 'value', splitLine: { lineStyle: { color: t.borderLight } }, ...axis },
    series: props.series.map((s) => ({
      type: 'bar',
      name: s.name,
      data: s.data,
      barMaxWidth: 32,
      itemStyle: { borderRadius: [4, 4, 0, 0] }
    }))
  } as Record<string, unknown>
})
</script>

<template>
  <ArChart :option="option" :height="height" />
</template>
