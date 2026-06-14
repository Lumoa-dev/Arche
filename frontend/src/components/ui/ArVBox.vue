<script setup lang="ts">
/**
 * ArVBox — 纵向弹性布局原语
 *
 * 类比 Qt 的 QVBoxLayout。子项默认纵向排列，
 * 配合 ArSpacer 可实现 Qt 风格的 stretch 控制。
 */
withDefaults(
  defineProps<{
    /** 子项间距（使用项目 spacing token 或任意 CSS 长度） */
    gap?: string
    /** 交叉轴对齐方式 */
    align?: 'start' | 'center' | 'end' | 'stretch' | 'baseline'
    /** 主轴对齐方式 */
    justify?: 'start' | 'center' | 'end' | 'space-between' | 'space-around' | 'space-evenly'
    /** 是否反向排列 */
    reverse?: boolean
  }>(),
  {
    gap: '',
    align: 'stretch',
    justify: 'start',
    reverse: false
  }
)
</script>

<template>
  <div
    class="ar-vbox"
    :class="[
      `ar-vbox--align-${align}`,
      `ar-vbox--justify-${justify}`,
      {
        'ar-vbox--reverse': reverse
      }
    ]"
    :style="gap ? { gap } : undefined"
  >
    <slot />
  </div>
</template>

<style scoped>
.ar-vbox {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.ar-vbox--reverse {
  flex-direction: column-reverse;
}

/* ── align ── */
.ar-vbox--align-start {
  align-items: flex-start;
}
.ar-vbox--align-center {
  align-items: center;
}
.ar-vbox--align-end {
  align-items: flex-end;
}
.ar-vbox--align-stretch {
  align-items: stretch;
}
.ar-vbox--align-baseline {
  align-items: baseline;
}

/* ── justify ── */
.ar-vbox--justify-start {
  justify-content: flex-start;
}
.ar-vbox--justify-center {
  justify-content: center;
}
.ar-vbox--justify-end {
  justify-content: flex-end;
}
.ar-vbox--justify-space-between {
  justify-content: space-between;
}
.ar-vbox--justify-space-around {
  justify-content: space-around;
}
.ar-vbox--justify-space-evenly {
  justify-content: space-evenly;
}
</style>
