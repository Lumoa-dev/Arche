<script setup lang="ts">
/**
 * ArGrid — 网格布局原语
 *
 * 类比 Qt 的 QGridLayout。基于 CSS Grid 实现，
 * 支持跨行跨列、行列模版、行列间距。
 * 配合 ArGridItem 使用来控制跨行跨列。
 */
withDefaults(
  defineProps<{
    /** 列模版（CSS grid-template-columns 值，如 "1fr 280px"） */
    columns?: string
    /** 行模版（CSS grid-template-rows 值） */
    rows?: string
    /** 行列间距（简写） */
    gap?: string
    /** 列间距 */
    columnGap?: string
    /** 行间距 */
    rowGap?: string
    /** 对齐方式 */
    align?: 'start' | 'center' | 'end' | 'stretch'
    /** 交叉轴对齐 */
    justify?: 'start' | 'center' | 'end' | 'stretch'
  }>(),
  {
    columns: '',
    rows: '',
    gap: '',
    columnGap: '',
    rowGap: '',
    align: 'stretch',
    justify: 'stretch'
  }
)
</script>

<template>
  <div
    class="ar-grid"
    :class="[`ar-grid--align-${align}`, `ar-grid--justify-${justify}`]"
    :style="{
      gridTemplateColumns: columns || undefined,
      gridTemplateRows: rows || undefined,
      gap: gap || undefined,
      columnGap: columnGap || undefined,
      rowGap: rowGap || undefined
    }"
  >
    <slot />
  </div>
</template>

<style scoped>
.ar-grid {
  display: grid;
  min-width: 0;
}

/* ── align ── */
.ar-grid--align-start {
  align-items: start;
}
.ar-grid--align-center {
  align-items: center;
}
.ar-grid--align-end {
  align-items: end;
}
.ar-grid--align-stretch {
  align-items: stretch;
}

/* ── justify ── */
.ar-grid--justify-start {
  justify-items: start;
}
.ar-grid--justify-center {
  justify-items: center;
}
.ar-grid--justify-end {
  justify-items: end;
}
.ar-grid--justify-stretch {
  justify-items: stretch;
}
</style>
