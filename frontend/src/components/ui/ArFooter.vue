<script setup lang="ts">
/**
 * ArFooter — 页脚布局原语
 *
 * 纯布局组件，只关心结构和样式。
 * 所有内容通过默认 slot 注入。
 */
withDefaults(
  defineProps<{
    /** 是否显示分隔线 */
    bordered?: boolean
  }>(),
  {
    bordered: false
  }
)
</script>

<template>
  <footer class="ar-footer" :class="{ 'ar-footer--bordered': bordered }">
    <slot />
  </footer>
</template>

<style scoped>
.ar-footer {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-md);
  font-size: var(--text-xs);
  color: var(--text-tertiary);
  gap: var(--spacing-sm);
}

.ar-footer--bordered {
  border-top: 1px solid var(--border-color);
}
</style>
