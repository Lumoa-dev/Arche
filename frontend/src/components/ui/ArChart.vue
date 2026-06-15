<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import * as echarts from 'echarts'

const props = withDefaults(
  defineProps<{
    /** ECharts option */
    option?: Record<string, unknown>
    /** 是否不渲染（用于异步加载） */
    lazy?: boolean
    /** 容器高度 */
    height?: number | string
  }>(),
  {
    option: () => ({}),
    lazy: false,
    height: 300
  }
)

const chartRef = ref<HTMLDivElement>()
const instance = ref<echarts.ECharts | null>(null)
const resizeObserver = ref<ResizeObserver | null>(null)

function initChart() {
  if (!chartRef.value || props.lazy) return
  instance.value?.dispose()
  instance.value = echarts.init(chartRef.value, undefined, { renderer: 'canvas' })
  instance.value.setOption(props.option)
  // ResizeObserver 代替 window.resize
  resizeObserver.value = new ResizeObserver(() => {
    instance.value?.resize()
  })
  resizeObserver.value.observe(chartRef.value)
}

function updateChart() {
  if (!instance.value) return
  instance.value.setOption(props.option, { notMerge: false })
}

onMounted(initChart)

watch(() => props.option, updateChart, { deep: true, immediate: true })

onUnmounted(() => {
  resizeObserver.value?.disconnect()
  instance.value?.dispose()
  instance.value = null
})
</script>

<template>
  <div
    ref="chartRef"
    class="ar-chart"
    :style="{ height: typeof height === 'number' ? height + 'px' : height }"
  />
</template>

<style scoped>
.ar-chart {
  width: 100%;
  min-height: 100px;
}
</style>
