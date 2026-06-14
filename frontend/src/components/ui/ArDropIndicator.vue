<script setup lang="ts">
/**
 * ArDropIndicator — 拖拽放置指示器
 *
 * 可排序列表中通用的「放置目标指示线」。
 * 水平横线 + 中间标签，指示拖拽项可放置的位置。
 * 是基础 UI 原语，不包含任何业务逻辑。
 */
defineProps<{
  /** 标签文字，如「移动到此处」 */
  label?: string
}>()
</script>

<template>
  <div class="ar-drop-indicator">
    <span class="ar-drop-indicator__label">{{ label || '移动到此处' }}</span>
  </div>
</template>

<style scoped>
.ar-drop-indicator {
  position: absolute;
  top: -1px;
  left: -1px;
  right: -1px;
  display: flex;
  align-items: center;
  gap: 8px;
  pointer-events: none;
  z-index: 5;
}

.ar-drop-indicator::before,
.ar-drop-indicator::after {
  content: '';
  flex: 1;
  height: 2px;
  background: var(--primary-color);
  border-radius: 1px;
}

.ar-drop-indicator__label {
  font-size: 11px;
  font-weight: var(--font-weight-semibold);
  color: var(--primary-color);
  background: var(--surface-color);
  padding: 0 8px;
  white-space: nowrap;
  border-radius: var(--radius-sm);
  line-height: 22px;
}
</style>
