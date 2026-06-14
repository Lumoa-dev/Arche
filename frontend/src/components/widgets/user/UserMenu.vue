<script setup lang="ts">
import type { Component } from 'vue'
import { useRoute } from 'vue-router'

export interface MenuItem {
  title: string
  path: string
  icon: Component
}

const props = withDefaults(
  defineProps<{
    items: MenuItem[]
    currentPath?: string
  }>(),
  {
    currentPath: ''
  }
)

const route = useRoute()

const isActive = (path: string) => {
  const current = props.currentPath || route.path
  return current === path || current.startsWith(path + '/')
}
</script>

<template>
  <nav class="user-menu">
    <RouterLink
      v-for="item in items"
      :key="item.path"
      :to="item.path"
      class="user-menu__item"
      :class="{ 'user-menu__item--active': isActive(item.path) }"
    >
      <component :is="item.icon" class="user-menu__icon" />
      <span class="user-menu__title">{{ item.title }}</span>
    </RouterLink>
  </nav>
</template>

<style scoped>
.user-menu {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.user-menu__item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 16px;
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  text-decoration: none;
  font-size: 14px;
  font-weight: var(--font-weight-medium);
  transition:
    background-color var(--transition-fast),
    color var(--transition-fast);
}

.user-menu__item:hover {
  background: var(--primary-light-color);
  color: var(--primary-color);
}

.user-menu__item--active {
  background: var(--primary-color);
  color: var(--text-on-primary, #fff);
}

.user-menu__item--active:hover {
  background: var(--primary-hover-color);
  color: var(--text-on-primary, #fff);
}

.user-menu__icon {
  font-size: 20px;
  flex-shrink: 0;
}

.user-menu__title {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
