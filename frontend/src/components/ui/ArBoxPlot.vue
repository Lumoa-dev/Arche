<script setup lang="ts">
import { computed } from 'vue'
import { useArChartTheme } from '@/composables/useArChartTheme'
import ArChart from './ArChart.vue'

const props = withDefaults(
  defineProps<{
    /** 每个类别：[min, Q1, median, Q3, max] */
    data?: { name: string; value: number[] }[]
    height?: number
  }>(),
  {
    data: () => [],
    height: 300
  }
)

const { tokens, axisStyle, tooltipStyle } = useArChartTheme()

const option = computed(() => {
  const t = tokens()
  const axis = axisStyle()
  return {
    tooltip: { ...tooltipStyle(), trigger: 'item' },
    grid: { left: 40, right: 40, top: 16, bottom: 24 },
    xAxis: {
      type: 'category',
      data: props.data.map((d) => d.name),
      ...axis,
    },
    yAxis: { type: 'value', splitLine: { lineStyle: { color: t.borderLight } }, ...axis },
    series: [
      {
        type: 'boxplot',
        data: props.data.map((d) => d.value),
        itemStyle: { color: t.accent, borderColor: t.accentHover },
      },
    ],
  } as Record<string, unknown>
})
</script>

<template>
  <ArChart :option="option" :height="height" />
</template>
