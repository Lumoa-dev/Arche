<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { NIcon } from 'naive-ui'
import {
  AppsOutline,
  PersonOutline,
  DocumentTextOutline,
  SettingsOutline,
  MenuOutline,
  AddOutline,
  CloseOutline
} from '@vicons/ionicons5'
import { useUserStore } from '@/lib/store/modules/user'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

const isAdmin = computed(() => (userStore.userInfo?.level ?? 5) === 0)
const showMobileMenu = ref(false)

// 管理组菜单
const adminGroups = [
  { label: '用户管理', icon: PersonOutline, to: '/admin/users' },
  { label: '内容管理', icon: DocumentTextOutline, to: '/admin/content' },
  { label: '运维管理', icon: SettingsOutline, to: '/admin/ops' }
]

// 快捷方式
const SHORTCUTS_KEY = 'console_shortcuts'
const shortcuts = ref<Array<{ label: string; to: string; icon?: string }>>([])

const loadShortcuts = () => {
  try {
    const data = localStorage.getItem(SHORTCUTS_KEY)
    shortcuts.value = data ? JSON.parse(data) : []
  } catch {
    shortcuts.value = []
  }
}

const saveShortcuts = () => {
  localStorage.setItem(SHORTCUTS_KEY, JSON.stringify(shortcuts.value))
}

const addShortcut = () => {
  const label = prompt('请输入快捷方式名称：')
  if (!label) return
  const to = prompt('请输入路由路径：')
  if (!to) return
  // 防重复
  if (shortcuts.value.some((s) => s.to === to)) return
  shortcuts.value.push({ label, to })
  saveShortcuts()
}

const removeShortcut = (index: number) => {
  shortcuts.value.splice(index, 1)
  saveShortcuts()
}

const isActive = (path: string) => route.path === path

// 初始化加载
loadShortcuts()

// 路径变化时重新加载（跨页面时可更新状态）
watch(() => route.path, loadShortcuts)
</script>

<template>
  <div class="console-shell">
    <div v-if="showMobileMenu" class="mobile-overlay" @click="showMobileMenu = false" />
    <aside class="console-sidebar" :class="{ 'sidebar-mobile-visible': showMobileMenu }">
      <nav class="sidebar-nav">
        <!-- 控制台首页 -->
        <button
          class="nav-btn"
          :class="{ active: isActive('/console') }"
          @click="router.push('/console')"
        >
          <NIcon size="18"><AppsOutline /></NIcon>
          <span>控制台首页</span>
        </button>

        <div class="section-divider"></div>

        <!-- 管理组（仅管理员） -->
        <template v-if="isAdmin">
          <button
            v-for="group in adminGroups"
            :key="group.to"
            class="nav-btn"
            :class="{ active: isActive(group.to) }"
            @click="router.push(group.to)"
          >
            <NIcon size="18"><component :is="group.icon" /></NIcon>
            <span>{{ group.label }}</span>
          </button>

          <div class="section-divider"></div>
        </template>

        <!-- 快捷访问组 -->
        <div class="shortcuts-header">
          <span class="shortcuts-title">快捷访问</span>
        </div>
        <template v-if="shortcuts.length > 0">
          <div v-for="(shortcut, index) in shortcuts" :key="shortcut.to" class="shortcut-item">
            <button
              class="nav-btn shortcut-btn"
              :class="{ active: isActive(shortcut.to) }"
              @click="router.push(shortcut.to)"
            >
              <NIcon size="18"><AppsOutline /></NIcon>
              <span>{{ shortcut.label }}</span>
            </button>
            <button
              class="shortcut-remove"
              @click.stop="removeShortcut(index)"
              title="移除快捷方式"
            >
              <NIcon size="14"><CloseOutline /></NIcon>
            </button>
          </div>
        </template>
        <button class="nav-btn add-shortcut-btn" @click="addShortcut">
          <NIcon size="18"><AddOutline /></NIcon>
          <span>添加快捷方式</span>
        </button>
      </nav>
    </aside>
    <main class="console-content">
      <button
        class="mobile-menu-btn"
        aria-label="导航菜单"
        @click="showMobileMenu = !showMobileMenu"
      >
        <NIcon size="20"><MenuOutline /></NIcon>
      </button>
      <slot />
    </main>
  </div>
</template>

<style scoped>
.console-shell {
  display: grid;
  grid-template-columns: 200px 1fr;
  gap: 16px;
  align-items: start;
}

.console-sidebar {
  position: sticky;
  top: 16px;
  background: rgba(255, 248, 236, 0.72);
  border: 1px solid rgba(130, 95, 65, 0.14);
  border-radius: var(--radius-md);
  padding: 12px;
}

.sidebar-nav {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.nav-btn {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 10px;
  border: none;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--text-secondary);
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s ease;
  text-align: left;
  width: 100%;
}

.nav-btn:hover {
  background: rgba(154, 90, 47, 0.08);
  color: var(--primary-color);
}

.nav-btn.active {
  background: rgba(154, 90, 47, 0.12);
  color: var(--primary-color);
  font-weight: 600;
}

/* 分隔线 */
.section-divider {
  height: 1px;
  background: rgba(130, 95, 65, 0.12);
  margin: 8px 8px;
}

/* 快捷访问组标签 */
.shortcuts-header {
  padding: 4px 8px 10px;
  border-bottom: 1px solid rgba(130, 95, 65, 0.1);
  margin-bottom: 6px;
  margin-top: 4px;
}

.shortcuts-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-tertiary);
  letter-spacing: 0.08em;
}

/* 快捷方式项容器 */
.shortcut-item {
  display: flex;
  align-items: center;
  gap: 2px;
}

.shortcut-btn {
  flex: 1;
  min-width: 0;
}

/* 快捷方式删除按钮 */
.shortcut-remove {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border: none;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--text-quaternary);
  cursor: pointer;
  transition: all 0.2s ease;
  flex-shrink: 0;
}

.shortcut-remove:hover {
  color: #e74c3c;
  background: rgba(231, 76, 60, 0.08);
}

/* 添加快捷方式按钮 */
.add-shortcut-btn {
  border: 1px dashed rgba(130, 95, 65, 0.2);
  margin-top: 2px;
  opacity: 0.7;
}

.add-shortcut-btn:hover {
  border-color: var(--primary-color);
  opacity: 1;
}

.console-content {
  min-width: 0;
}

.mobile-menu-btn {
  display: none;
  border: none;
  background: rgba(255, 248, 236, 0.72);
  border-radius: var(--radius-sm);
  padding: 6px;
  cursor: pointer;
  color: var(--text-secondary);
  margin-bottom: 12px;
}

.mobile-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.3);
  z-index: 50;
  backdrop-filter: blur(2px);
}

@media (max-width: 860px) {
  .mobile-menu-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
  }

  .console-shell {
    grid-template-columns: 1fr;
  }

  .console-sidebar {
    position: fixed;
    top: 0;
    left: 0;
    bottom: 0;
    width: 240px;
    z-index: 100;
    transform: translateX(-100%);
    transition: transform 0.3s ease;
    display: block !important;
    border-radius: 0 var(--radius-md) var(--radius-md) 0;
    box-shadow: var(--shadow-lg);
  }

  .console-sidebar.sidebar-mobile-visible {
    transform: translateX(0);
  }
}
</style>
