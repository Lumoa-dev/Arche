<script setup lang="ts">
import { computed } from 'vue'
import { useArChartTheme } from '@/composables/useArChartTheme'
import ArChart from './ArChart.vue'

const props = withDefaults(
  defineProps<{
    data?: { name?: string; x: number; y: number; value?: number }[]
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
  const vals = props.data.map((d) => d.value ?? 1)
  const maxVal = Math.max(...vals, 1)
  return {
    tooltip: { ...tooltipStyle(), formatter: (p: { data: { name?: string; x: number; y: number } }) => `${p.data.name || ''} (${p.data.x}, ${p.data.y})` },
    grid: { left: 40, right: 40, top: 16, bottom: 24 },
    xAxis: { type: 'value', splitLine: { lineStyle: { color: t.borderLight } }, ...axis },
    yAxis: { type: 'value', splitLine: { lineStyle: { color: t.borderLight } }, ...axis },
    series: [
      {
        type: 'scatter',
        data: props.data.map((d) => ({
          name: d.name,
          value: [d.x, d.y, d.value ?? 1],
        })),
        symbolSize: (val: number[]) => Math.max(4, (val[2] / maxVal) * 24),
        itemStyle: { color: t.accent, opacity: 0.7 },
      },
    ],
  } as Record<string, unknown>
})
</script>

<template>
  <ArChart :option="option" :height="height" />
</template>
