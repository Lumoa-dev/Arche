<script setup lang="ts">
/**
 * ArSpacer — 弹性空白组件
 *
 * 在弹性布局中占据剩余空间，类比 Qt 的 addStretch()。
 * 不设 size 时 flex: 1 自动填充，设 size 时为固定尺寸的空白间隔。
 */
withDefaults(
  defineProps<{
    /** 固定尺寸（不设则 flex: 1 弹性填充） */
    size?: string | number
    /** 方向感知（仅对固定尺寸有效） */
    orientation?: 'horizontal' | 'vertical'
  }>(),
  {
    size: undefined,
    orientation: 'horizontal'
  }
)
</script>

<template>
  <div
    class="ar-spacer"
    :style="
      size != null
        ? orientation === 'vertical'
          ? { height: typeof size === 'number' ? size + 'px' : size }
          : { width: typeof size === 'number' ? size + 'px' : size }
        : { flex: '1 1 0%', minWidth: 0, minHeight: 0 }
    "
  />
</template>
