<script setup lang="ts">
/**
 * ArHBox — 横向弹性布局原语
 *
 * 类比 Qt 的 QHBoxLayout。子项默认依次横向排列，
 * 配合 ArSpacer 可实现 Qt 风格的 stretch 控制。
 * 不使用多余 DOM 包裹，直接作为 flex container。
 */
withDefaults(
  defineProps<{
    /** 子项间距（使用项目 spacing token 或任意 CSS 长度） */
    gap?: string
    /** 交叉轴对齐方式 */
    align?: 'start' | 'center' | 'end' | 'stretch' | 'baseline'
    /** 主轴对齐方式 */
    justify?: 'start' | 'center' | 'end' | 'space-between' | 'space-around' | 'space-evenly'
    /** 是否允许换行 */
    wrap?: boolean
    /** 是否反向排列 */
    reverse?: boolean
  }>(),
  {
    gap: '',
    align: 'center',
    justify: 'start',
    wrap: false,
    reverse: false
  }
)
</script>

<template>
  <div
    class="ar-hbox"
    :class="[
      `ar-hbox--align-${align}`,
      `ar-hbox--justify-${justify}`,
      {
        'ar-hbox--wrap': wrap,
        'ar-hbox--reverse': reverse
      }
    ]"
    :style="gap ? { gap } : undefined"
  >
    <slot />
  </div>
</template>

<style scoped>
.ar-hbox {
  display: flex;
  flex-direction: row;
  min-width: 0;
}

.ar-hbox--reverse {
  flex-direction: row-reverse;
}

.ar-hbox--wrap {
  flex-wrap: wrap;
}

/* ── align ── */
.ar-hbox--align-start {
  align-items: flex-start;
}
.ar-hbox--align-center {
  align-items: center;
}
.ar-hbox--align-end {
  align-items: flex-end;
}
.ar-hbox--align-stretch {
  align-items: stretch;
}
.ar-hbox--align-baseline {
  align-items: baseline;
}

/* ── justify ── */
.ar-hbox--justify-start {
  justify-content: flex-start;
}
.ar-hbox--justify-center {
  justify-content: center;
}
.ar-hbox--justify-end {
  justify-content: flex-end;
}
.ar-hbox--justify-space-between {
  justify-content: space-between;
}
.ar-hbox--justify-space-around {
  justify-content: space-around;
}
.ar-hbox--justify-space-evenly {
  justify-content: space-evenly;
}
</style>
