<script setup lang="ts">
import { computed } from 'vue'
import { useArChartTheme } from '@/composables/useArChartTheme'
import ArChart from './ArChart.vue'

const props = withDefaults(
  defineProps<{
    /** 雷达指示器 */
    indicators?: { name: string; max: number }[]
    /** 数据系列 */
    series?: { name: string; data: number[] }[]
    height?: number
  }>(),
  {
    indicators: () => [],
    series: () => [],
    height: 300
  }
)

const { palette, tooltipStyle, textStyle } = useArChartTheme()

const option = computed(() => ({
  color: palette(),
  tooltip: { ...tooltipStyle() },
  legend: {
    data: props.series.map((s) => s.name),
    ...textStyle(12),
    bottom: 0,
  },
  radar: {
    indicator: props.indicators,
    shape: 'polygon',
    splitNumber: 4,
    axisName: { ...textStyle(12), color: '#6b5e52' },
    splitLine: { lineStyle: { color: '#efe9e2' } },
    splitArea: {
      areaStyle: { color: ['rgba(194,70,46,0.02)', 'rgba(194,70,46,0.05)'] },
    },
    axisLine: { lineStyle: { color: '#e5ddd4' } },
  },
  series: [
    {
      type: 'radar',
      data: props.series.map((s) => ({ name: s.name, value: s.data })),
      lineStyle: { width: 1.5 },
      areaStyle: { opacity: 0.1 },
    },
  ],
}) as Record<string, unknown>)
</script>

<template>
  <ArChart :option="option" :height="height" />
</template>
