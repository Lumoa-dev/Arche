<script setup lang="ts">
defineSlots<{ default: void }>()
</script>

<template>
  <div class="alert-note">
    <slot />
  </div>
</template>

<style scoped>
.alert-note {
  margin-bottom: var(--spacing-md);
  padding: var(--spacing-sm) var(--spacing-md);
  background: var(--primary-light-color);
  border-left: 3px solid var(--primary-color);
  border-radius: var(--radius-sm);
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.5;
}
</style>
