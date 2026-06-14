<script setup lang="ts">
import { computed } from 'vue'
import { useArChartTheme } from '@/composables/useArChartTheme'
import ArChart from './ArChart.vue'

const props = withDefaults(
  defineProps<{
    /** 仪表盘指标 */
    indicators?: { name: string; value: number; max?: number }[]
    height?: number
  }>(),
  {
    indicators: () => [],
    height: 300
  }
)

const { tokens, textStyle } = useArChartTheme()

const option = computed(() => {
  const t = tokens()
  const ts = textStyle()
  return {
    series: props.indicators.map((ind, i) => {
      const max = ind.max ?? 100
      const angle = 360 / props.indicators.length
      const startAngle = -125 + angle * i
      return {
        type: 'gauge',
        center: ['50%', '55%'],
        radius: '90%',
        startAngle,
        endAngle: startAngle + 250,
        min: 0,
        max,
        splitNumber: 5,
        progress: { show: true, width: 6, itemStyle: { color: t.accent } },
        axisLine: {
          lineStyle: { width: 6, color: [[1, t.borderLight]] },
        },
        axisTick: { show: false },
        splitLine: { show: false },
        axisLabel: { show: false },
        detail: {
          ...ts,
          fontSize: 14,
          fontWeight: 600,
          color: t.textPrimary,
          formatter: `{value}`,
          offsetCenter: [0, '60%'],
        },
        title: {
          ...ts,
          fontSize: 11,
          color: t.textTertiary,
          offsetCenter: [0, '40%'],
        },
        data: [{ value: ind.value, name: ind.name }],
      }
    }),
  } as Record<string, unknown>
})
</script>

<template>
  <ArChart :option="option" :height="height" />
</template>
