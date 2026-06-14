<script setup lang="ts">
/**
 * ArPageHeader — 页面级标题区
 *
 * 统一页面标题、描述和操作区的布局。
 * 使用后页面无需再写 .page-header / .page-desc / .page-header-actions 样式。
 */
withDefaults(
  defineProps<{
    /** 页面标题 */
    title?: string
    /** 页面描述 */
    desc?: string
  }>(),
  {
    title: '',
    desc: ''
  }
)
</script>

<template>
  <div class="ar-page-header">
    <div class="ar-page-header__text">
      <h1 v-if="title" class="ar-page-header__title">{{ title }}</h1>
      <p v-if="desc" class="ar-page-header__desc">{{ desc }}</p>
      <slot name="text" />
    </div>
    <div v-if="$slots.default || $slots.actions" class="ar-page-header__actions">
      <slot name="actions" />
      <slot />
    </div>
  </div>
</template>

<style scoped>
.ar-page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--spacing-md);
}

.ar-page-header__text {
  flex: 1;
  min-width: 0;
}

.ar-page-header__title {
  margin: 0 0 4px;
  font-size: 26px;
  font-weight: var(--font-weight-bold);
  color: var(--color-text-primary);
  line-height: 1.3;
}

.ar-page-header__desc {
  margin: 0;
  font-size: 14px;
  color: var(--color-text-tertiary);
  line-height: 1.5;
}

.ar-page-header__actions {
  display: flex;
  gap: var(--spacing-sm);
  flex-shrink: 0;
  align-items: center;
}

@media (max-width: 768px) {
  .ar-page-header {
    flex-direction: column;
  }
}
</style>
