<template>
  <NConfigProvider
    :theme="theme"
    :theme-overrides="themeOverrides"
    :locale="zhCN"
    :date-locale="dateZhCN"
  >
    <NMessageProvider>
      <NDialogProvider>
        <NNotificationProvider>
          <NLoadingBarProvider>
            <div class="app-shell" :class="[`app-shell--${layoutMode}`]">
              <AppHeader
                v-if="showHeader"
                :layoutMode="layoutMode"
                @toggleSidebar="handleToggleSidebar"
              />

              <div
                class="app-body"
                :class="[
                  `app-body--${layoutMode}`,
                  { 'sidebar-collapsed': appStore.sidebarCollapsed }
                ]"
              >
                <AppSidebar
                  v-if="showSidebar"
                  :sidebarItems="sidebarItems"
                  :mode="sidebarMode"
                  :collapsed="appStore.sidebarCollapsed"
                  @close="handleCloseSidebar"
                />

                <main class="app-main">
                  <RouterView />
                </main>
              </div>

              <ArFooter v-if="showFooter" bordered>
                <span>© 2025 Arche. All rights reserved.</span>
                <ArDivider vertical />
                <RouterLink to="/about">关于</RouterLink>
              </ArFooter>
            </div>
          </NLoadingBarProvider>
        </NNotificationProvider>
      </NDialogProvider>
    </NMessageProvider>
  </NConfigProvider>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import {
  NConfigProvider,
  NMessageProvider,
  NDialogProvider,
  NNotificationProvider,
  NLoadingBarProvider,
  darkTheme,
  zhCN,
  dateZhCN,
  type GlobalThemeOverrides
} from 'naive-ui'
import ArFooter from '@/components/ui/ArFooter.vue'
import ArDivider from '@/components/ui/ArDivider.vue'
import AppHeader from '@/components/widgets/common/AppHeader.vue'
import AppSidebar from '@/components/widgets/common/AppSidebar.vue'
import { useAppStore } from '@/lib/store/modules/app'
import { usePermissionStore } from '@/lib/store/modules/permission'
import { buildLayoutMenus } from '@/lib/router/menu'
import { HomeOutline } from '@/icons'

const route = useRoute()
const appStore = useAppStore()
const permissionStore = usePermissionStore()

const themeOverrides: GlobalThemeOverrides = {
  common: {
    primaryColor: '#9a5a2f',
    primaryColorHover: '#b8743d',
    primaryColorPressed: '#6f3f22',
    successColor: '#4f7a57',
    warningColor: '#b98529',
    errorColor: '#b34c3f',
    borderRadius: '12px'
  },
  Progress: {
    railColor: 'rgba(130, 95, 65, 0.1)'
  },
  Tag: {
    color: 'rgba(154, 90, 47, 0.08)',
    border: 'none',
    textColor: '#5f5b54',
    closeColor: 'rgba(130, 95, 65, 0.35)'
  },
  Button: {
    textColorGhost: '#5f5b54',
    border: '1px solid rgba(130, 95, 65, 0.14)',
    borderHover: '1px solid #b8743d',
    borderPressed: '1px solid #6f3f22',
    borderFocus: '1px solid #b8743d'
  },
  Popover: {
    color: 'var(--surface-color)',
    border: '1px solid var(--border-color)',
    borderRadius: 'var(--radius-md)',
    fontSize: '12px'
  },
  Select: {
    menuColor: 'var(--surface-color)',
    menuBorder: '1px solid var(--border-color)',
    menuBorderRadius: 'var(--radius-md)',
    menuBoxShadow: 'var(--shadow-lg)',
    optGroupTextColor: 'var(--text-secondary)',
    optGroupFontSize: '11px'
  },
  InternalSelectMenu: {
    color: 'var(--surface-color)',
    border: '1px solid var(--border-color)',
    borderRadius: 'var(--radius-md)',
    boxShadow: 'var(--shadow-lg)',
    optionColor: 'transparent',
    optionColorHover: 'var(--primary-light-color)',
    optionColorActive: 'var(--primary-light-color)',
    optionTextColor: 'var(--text-primary)',
    optionTextColorHover: 'var(--primary-color)',
    optionTextColorActive: 'var(--primary-color)',
    optionFontSize: '12px',
    optionHeight: '28px'
  },
  Pagination: {
    itemFontSizeSmall: '12px',
    itemFontSizeActive: '12px',
    itemTextColor: 'var(--text-secondary)',
    itemTextColorHover: 'var(--primary-color)',
    itemTextColorActive: 'var(--primary-color)',
    itemColor: 'transparent',
    itemColorHover: 'var(--primary-light-color)',
    itemColorActive: 'var(--primary-light-color)',
    itemBorder: '1px solid var(--border-color)',
    itemBorderHover: '1px solid var(--primary-color)',
    itemBorderActive: '1px solid var(--primary-color)',
    itemBorderRadius: 'var(--radius-sm)',
    buttonColor: 'transparent',
    buttonColorHover: 'var(--primary-light-color)',
    buttonBorder: '1px solid var(--border-color)',
    buttonBorderHover: '1px solid var(--primary-color)',
    buttonIconColor: 'var(--text-tertiary)',
    buttonIconColorHover: 'var(--primary-color)',
    inputBorderColor: 'var(--border-color)',
    inputBorderColorHover: 'var(--primary-color)',
    inputBorderColorFocus: 'var(--primary-color)',
    selectBorderColor: 'var(--border-color)',
    selectBorderColorHover: 'var(--primary-color)',
    selectBorderColorFocus: 'var(--primary-color)',
    prefixFontSize: '12px',
    suffixFontSize: '12px'
  }
}

/** 当前布局模式，从路由 meta 读取 */
const layoutMode = computed<string>(() => {
  return (route.meta.layout as string) || 'guest'
})

/** 是否显示顶部导航栏 */
const showHeader = computed(() => {
  return ['guest', 'user', 'admin'].includes(layoutMode.value)
})

/** 是否显示侧边栏 */
const showSidebar = computed(() => {
  if (layoutMode.value === 'guest') return sidebarItems.value.length > 0
  return ['user', 'admin'].includes(layoutMode.value)
})

/** 是否显示页脚 */
const showFooter = computed(() => {
  return layoutMode.value === 'guest'
})

/** 侧边栏模式映射 */
const sidebarMode = computed<'thin' | 'normal' | 'grouped'>(() => {
  const modeMap: Record<string, 'thin' | 'normal' | 'grouped'> = {
    guest: 'thin',
    user: 'normal',
    admin: 'grouped'
  }
  return modeMap[layoutMode.value] || 'thin'
})

/** 当前布局模式的侧边栏条目 */
const sidebarItems = computed(() => {
  if (layoutMode.value === 'guest') return []

  // user 模式：从权限路由构建菜单
  if (layoutMode.value === 'user') {
    const menus = buildLayoutMenus(permissionStore.routes, 'user')
    const homeMenu = { title: '首页', path: '/', icon: HomeOutline }
    return [homeMenu, ...menus]
  }

  // admin 模式：从权限路由构建菜单
  if (layoutMode.value === 'admin') {
    const menus = buildLayoutMenus(permissionStore.routes, 'admin')
    return menus
  }

  return []
})

// 主题切换
const theme = computed(() => {
  return appStore.theme === 'dark' ? darkTheme : null
})

/** 切换侧边栏折叠状态 */
const handleToggleSidebar = () => {
  appStore.toggleSidebar()
}

/** 移动端关闭侧边栏 */
const handleCloseSidebar = () => {
  if (appStore.isMobile) {
    appStore.setSidebarCollapsed(true)
  }
}
</script>

<style scoped>
.app-shell {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--bg-gradient-light);
  color: var(--text-primary);
}

.app-body {
  display: flex;
  flex: 1;
  padding-top: 56px;
}

.app-main {
  flex: 1;
  padding: var(--content-padding);
  min-width: 0;
  transition: margin-left var(--transition-slow) var(--ease-out-spring);
}

/* Guest 模式：侧边栏宽度 180px */
.app-body--guest .app-main {
  margin-left: 0;
}

/* User/Admin 模式：侧边栏宽度 240px */
.app-body--user .app-main,
.app-body--admin .app-main {
  margin-left: 240px;
}

/* 折叠时：侧边栏宽度 64px */
.app-body--user.sidebar-collapsed .app-main,
.app-body--admin.sidebar-collapsed .app-main {
  margin-left: 64px;
}

/* 移动端：无侧边栏外边距 */
@media (max-width: 992px) {
  .app-main {
    margin-left: 0 !important;
  }
}
</style>
