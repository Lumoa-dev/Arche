<script setup lang="ts">
defineProps<{
  /** 用户名称（中间） */
  username?: string
}>()
</script>

<template>
  <span class="ar-user-badge">
    <span v-if="$slots.left" class="ar-user-badge__left">
      <slot name="left" />
    </span>
    <span class="ar-user-badge__name">{{ username }}</span>
    <span v-if="$slots.right" class="ar-user-badge__right">
      <slot name="right" />
    </span>
  </span>
</template>

<style scoped>
.ar-user-badge {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  font-family: var(--font-sans);
  font-size: var(--text-sm);
  line-height: 1;
  white-space: nowrap;
}

.ar-user-badge__name {
  font-weight: var(--weight-medium);
  color: var(--color-text-primary);
}

.ar-user-badge__left,
.ar-user-badge__right {
  display: inline-flex;
  align-items: center;
}
</style>
