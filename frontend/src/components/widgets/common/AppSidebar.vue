<script setup lang="ts">
/**
 * AppSidebar — 全局侧边导航栏
 *
 * 使用 ArSideNav 提供导航容器，通过 props 驱动内容。
 * 不包含任何自定义 CSS。
 */
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import type { Component } from 'vue'
import ArSideNav from '@/components/ui/ArSideNav.vue'
import type { ArNavItem, ArNavGroup } from '@/components/ui/ArSideNav.vue'
import { useAppStore } from '@/lib/store/modules/app'

interface SidebarItem {
  title: string
  path: string
  icon?: Component
}

const props = withDefaults(
  defineProps<{
    sidebarItems: SidebarItem[]
    mode: 'thin' | 'normal' | 'grouped'
    collapsed: boolean
    currentPath?: string
  }>(),
  {
    currentPath: ''
  }
)

const emit = defineEmits<{
  close: []
}>()

const router = useRouter()
const route = useRoute()
const appStore = useAppStore()

/** 是否有可见的条目（guest 模式无条目时不渲染侧栏） */
const hasItems = computed(() => {
  return props.sidebarItems.length > 0
})

/** 当前活跃路径 */
const activeId = computed(() => {
  return props.currentPath || route.path
})

/** 转换为 ArNavItem 格式 */
const flatItems = computed<ArNavItem[]>(() => {
  return props.sidebarItems.map((item) => ({
    id: item.path,
    label: item.title,
    icon: item.icon
  }))
})

/** 分组模式下的条目（所有条目归入一个分组） */
const groupedItems = computed<ArNavGroup[]>(() => {
  if (props.mode !== 'grouped') return []
  return [
    {
      id: 'main',
      title: '系统管理',
      items: flatItems.value
    }
  ]
})

/** 导航选择处理 */
const handleSelect = (id: string) => {
  router.push(id)
}
</script>

<template>
  <ArSideNav
    v-if="hasItems"
    :mode="mode"
    :items="flatItems"
    :groups="groupedItems"
    :collapsed="collapsed"
    :activeId="activeId"
    position="left"
    @select="handleSelect"
  />

  <!-- Mobile overlay -->
  <div
    v-if="hasItems && appStore.isMobile && !collapsed"
    style="position: fixed; inset: 0; background: rgba(0, 0, 0, 0.3); z-index: 89"
    @click="emit('close')"
  />
</template>
