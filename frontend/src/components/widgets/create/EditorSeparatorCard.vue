<script setup lang="ts">
/**
 * EditorSeparatorCard — 分隔线卡片（非可编辑）
 *
 * 在段落列表中独立占位，显示一条水平分隔线。
 * 本身无交互，仅作为视觉分割。
 */
</script>

<template>
  <div class="separator-card">
    <div class="separator-card__line" />
  </div>
</template>

<style scoped>
.separator-card {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 12px 24px;
  user-select: none;
}

.separator-card__line {
  width: 100%;
  height: 0;
  border-top: 1px solid var(--border-color);
}
</style>
