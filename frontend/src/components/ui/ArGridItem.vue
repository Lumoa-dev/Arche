<script setup lang="ts">
/**
 * ArGridItem — 网格项
 *
 * 配合 ArGrid 使用的网格子项，支持跨行跨列。
 */
withDefaults(
  defineProps<{
    /** 跨列数 */
    colSpan?: number | string
    /** 列起始位置 */
    colStart?: number | string
    /** 跨行数 */
    rowSpan?: number | string
    /** 行起始位置 */
    rowStart?: number | string
  }>(),
  {
    colSpan: undefined,
    colStart: undefined,
    rowSpan: undefined,
    rowStart: undefined
  }
)
</script>

<template>
  <div
    class="ar-grid-item"
    :style="{
      gridColumn: colSpan != null ? `span ${colSpan}` : colStart != null ? colStart : undefined,
      gridRow: rowSpan != null ? `span ${rowSpan}` : rowStart != null ? rowStart : undefined
    }"
  >
    <slot />
  </div>
</template>

<style scoped>
.ar-grid-item {
  min-width: 0;
}
</style>
