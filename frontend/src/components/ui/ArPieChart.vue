<script setup lang="ts">
import { computed } from 'vue'
import { useArChartTheme } from '@/composables/useArChartTheme'
import ArChart from './ArChart.vue'

const props = withDefaults(
  defineProps<{
    data?: { name: string; value: number }[]
    height?: number
    /** 是否环形 */
    donut?: boolean
    /** 是否玫瑰图 */
    rose?: boolean
  }>(),
  {
    data: () => [],
    height: 300,
    donut: false,
    rose: false
  }
)

const { palette, tooltipStyle, tokens } = useArChartTheme()

const option = computed(() => {
  const t = tokens()
  return {
    color: palette(),
    tooltip: {
      ...tooltipStyle(),
      trigger: 'item',
      formatter: '{b}: {c} ({d}%)'
    },
    series: [
      {
        type: 'pie',
        data: props.data,
        radius: props.donut ? ['40%', '65%'] : '60%',
        roseType: props.rose ? 'area' : undefined,
        label: {
          show: true,
          fontSize: 12,
          color: t.textSecondary,
          formatter: '{b}'
        },
        labelLine: {
          lineStyle: { color: t.borderLight }
        },
        itemStyle: {
          borderRadius: 4,
          borderColor: '#fff',
          borderWidth: 2
        },
        emphasis: {
          itemStyle: {
            shadowBlur: 10,
            shadowColor: 'rgba(0, 0, 0, 0.15)'
          }
        }
      }
    ]
  }
}) as Record<string, unknown>
</script>

<template>
  <ArChart :option="option" :height="height" />
</template>
