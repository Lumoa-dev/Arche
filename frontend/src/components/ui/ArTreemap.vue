<script setup lang="ts">
import { computed } from 'vue'
import { useArChartTheme } from '@/composables/useArChartTheme'
import ArChart from './ArChart.vue'

export interface TreemapNode {
  name: string
  value?: number
  children?: TreemapNode[]
}

const props = withDefaults(
  defineProps<{
    data?: TreemapNode[]
    height?: number
  }>(),
  {
    data: () => [],
    height: 350
  }
)

const { palette, tooltipStyle } = useArChartTheme()

const option = computed(() => ({
  tooltip: { ...tooltipStyle(), formatter: '{b}: {c}' },
  series: [
    {
      type: 'treemap',
      data: props.data,
      roam: false,
      width: '100%',
      height: '100%',
      label: {
        show: true,
        fontSize: 12,
        color: '#fff',
        textShadowColor: 'rgba(0,0,0,0.3)',
        textShadowBlur: 2,
      },
      itemStyle: {
        borderColor: '#fff',
        borderWidth: 2,
        borderRadius: 4,
      },
      levels: [
        { colorSaturation: [0.3, 0.6], colorMappingBy: 'value' },
      ],
    },
  ],
}) as Record<string, unknown>)
</script>

<template>
  <ArChart :option="option" :height="height" />
</template>
