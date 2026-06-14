<script setup lang="ts">
import { computed } from 'vue'
import { useArChartTheme } from '@/lib/composables/useArChartTheme'
import ArChart from './ArChart.vue'

export interface SankeyLink {
  source: string
  target: string
  value: number
}

const props = withDefaults(
  defineProps<{
    nodes?: { name: string }[]
    links?: SankeyLink[]
    height?: number
  }>(),
  {
    nodes: () => [],
    links: () => [],
    height: 400
  }
)

const { palette, tooltipStyle, tokens } = useArChartTheme()

const option = computed(
  () =>
    ({
      color: palette(),
      tooltip: { ...tooltipStyle(), trigger: 'item', formatter: '{b}: {c}' },
      series: [
        {
          type: 'sankey',
          layout: 'none',
          layoutIterations: 32,
          nodeWidth: 16,
          nodeGap: 10,
          data: props.nodes,
          links: props.links,
          label: {
            fontSize: 12,
            color: '#6b5e52'
          },
          lineStyle: {
            color: 'gradient',
            curveness: 0.5
          },
          emphasis: {
            focus: 'adjacency',
            lineStyle: { opacity: 0.6 }
          }
        }
      ]
    }) as Record<string, unknown>
)
</script>

<template>
  <ArChart :option="option" :height="height" />
</template>
