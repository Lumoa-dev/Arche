<script setup lang="ts">
/**
 * AppHeader — 全局顶部导航栏
 *
 * 使用 ArTopNav 提供布局容器，通过 slot 注入业务内容。
 * 不包含任何自定义布局 CSS，所有布局由 ArTopNav 提供。
 */
import { computed, ref, onMounted, onBeforeUnmount } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { NIcon } from 'naive-ui'
import { SearchOutline, PersonOutline, SettingsOutline, LogOutOutline } from '@vicons/ionicons5'
import ArTopNav from '@/components/ui/ArTopNav.vue'
import ArAvatar from '@/components/ui/ArAvatar.vue'
import SiteLogo from '@/components/widgets/common/SiteLogo.vue'
import { useUserStore } from '@/lib/store/modules/user'
import { useAppStore } from '@/lib/store/modules/app'
import { useSearchStore } from '@/lib/store/modules/search'
import type { Suggestion } from '@/lib/store/modules/search'

const props = defineProps<{
  layoutMode: 'guest' | 'user' | 'admin'
}>()

const emit = defineEmits<{
  toggleSidebar: []
}>()

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()
const appStore = useAppStore()
const searchStore = useSearchStore()

const showUserMenu = ref(false)
const selectedIndex = ref(-1)
const searchWrapRef = ref<HTMLElement | null>(null)
const repoUrl = 'https://github.com/jamnodesmith/Arche'

const isLoggedIn = computed(() => userStore.isLoggedIn)
const isAdmin = computed(() => (userStore.userInfo?.level ?? 5) === 0)

/** 当前页面的搜索作用域（从路由 meta 读取） */
const searchScope = computed(() => {
  const scope = route.meta?.searchScope as
    | { type?: string; placeholder?: string; label?: string }
    | undefined
  return scope ?? null
})

const searchPlaceholder = computed(() => searchScope.value?.placeholder ?? '搜索...')

/** 面包屑 */
const breadcrumb = computed(() => {
  const path = route.path
  const layoutLabel = props.layoutMode === 'admin' ? '管理后台' : '首页'
  if (path === '/') return [layoutLabel]

  const routeName = route.name
  if (routeName && typeof routeName === 'string') {
    return [layoutLabel, routeName]
  }
  return [layoutLabel, '页面']
})

/** 用户输入处理 */
const onSearchInput = (e: Event) => {
  const target = e.target as HTMLInputElement
  searchStore.setKeyword(target.value)
  selectedIndex.value = -1
}

/** 回车搜索 */
const onSearchEnter = () => {
  const kw = searchStore.keyword.trim()
  if (!kw) return

  // 如果有选中的建议，跳转
  if (selectedIndex.value >= 0 && selectedIndex.value < searchStore.suggestions.length) {
    const item = searchStore.suggestions[selectedIndex.value]
    if (item) navigateToSuggestion(item)
    return
  }

  // 如果有建议列表，跳转到第一个
  if (searchStore.hasSuggestions) {
    const item = searchStore.suggestions[0]
    if (item) navigateToSuggestion(item)
    return
  }

  // 否则根据 scope 走搜索
  const scope = searchScope.value
  if (scope?.type === 'user') {
    router.push({ path: '/admin/users/list', query: { q: kw } })
  } else if (scope?.type === 'content') {
    router.push({ path: '/admin/content/moderation', query: { q: kw } })
  } else {
    router.push({ path: '/explore', query: { q: kw || undefined } })
  }

  searchStore.clearSearch()
}

/** 建议导航（上下键） */
const onSuggestionNavigate = (dir: 'up' | 'down') => {
  const len = searchStore.suggestions.length
  if (len === 0) return

  if (dir === 'down') {
    selectedIndex.value = selectedIndex.value < len - 1 ? selectedIndex.value + 1 : 0
  } else {
    selectedIndex.value = selectedIndex.value > 0 ? selectedIndex.value - 1 : len - 1
  }
}

/** 点击建议 */
const onSuggestionClick = (item: Suggestion) => {
  navigateToSuggestion(item)
}

/** 跳转到建议目标 */
const navigateToSuggestion = (item: Suggestion) => {
  searchStore.clearSearch()
  selectedIndex.value = -1
  if (item.url) {
    router.push(item.url)
  }
}

const handleLogout = async () => {
  showUserMenu.value = false
  await userStore.logout()
  router.push('/')
}

const goToProfile = () => {
  router.push('/profile')
  showUserMenu.value = false
}

const goToHome = () => {
  router.push('/')
  showUserMenu.value = false
}

/** 点击外部关闭下拉 */
const handleClickOutside = (e: MouseEvent) => {
  const target = e.target as HTMLElement
  if (!target.closest('.ar-top-nav__right') && !target.closest('.user-menu-wrap')) {
    showUserMenu.value = false
  }
  // 点击搜索外部关闭建议面板
  if (searchWrapRef.value && !searchWrapRef.value.contains(target)) {
    searchStore.deactivate()
  }
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
})

onBeforeUnmount(() => {
  document.removeEventListener('click', handleClickOutside)
})
</script>

<template>
  <ArTopNav
    :variant="layoutMode"
    :showMenuToggle="layoutMode !== 'guest'"
    @toggleSidebar="emit('toggleSidebar')"
  >
    <template #left>
      <SiteLogo size="md" />
    </template>

    <!-- 中心区域：导航菜单 / 面包屑 + 全局搜索 -->
    <nav v-if="layoutMode === 'guest'" class="nav-menu">
      <RouterLink to="/" class="nav-item" :class="{ active: $route.path === '/' }">首页</RouterLink>
      <RouterLink to="/explore" class="nav-item">探索</RouterLink>
      <RouterLink v-if="isLoggedIn" to="/create" class="nav-item">创作</RouterLink>
      <RouterLink v-if="isLoggedIn" to="/assets" class="nav-item">素材库</RouterLink>
      <RouterLink v-if="isLoggedIn" to="/tasks" class="nav-item">托管任务</RouterLink>
      <RouterLink to="/github" class="nav-item">GitHub</RouterLink>
    </nav>
    <div v-else class="breadcrumb">
      <span v-for="(item, index) in breadcrumb" :key="index">
        {{ item }}
        <span v-if="index < breadcrumb.length - 1" class="breadcrumb-sep">/</span>
      </span>
    </div>

    <!-- 全局搜索栏（所有模式下显示） -->
    <div class="search-section" :class="{ 'search-section--compact': layoutMode !== 'guest' }">
      <div class="search-wrap" ref="searchWrapRef">
        <NIcon class="search-leading-icon" size="17" aria-hidden="true">
          <SearchOutline />
        </NIcon>
        <input
          :value="searchStore.keyword"
          class="search-input"
          type="search"
          :placeholder="searchPlaceholder"
          aria-label="全局搜索"
          @input="onSearchInput"
          @focus="searchStore.activate()"
          @blur="searchStore.deactivate()"
          @keydown.enter="onSearchEnter"
          @keydown.down.prevent="onSuggestionNavigate('down')"
          @keydown.up.prevent="onSuggestionNavigate('up')"
          @keydown.escape="searchStore.deactivate()"
        />
        <!-- 加载指示器 -->
        <div v-if="searchStore.loading" class="search-loading">
          <span class="loading-dot"></span>
        </div>
      </div>

      <!-- 下拉建议面板 -->
      <Transition name="suggestions-fade">
        <div
          v-if="
            searchStore.active &&
            searchStore.hasContent &&
            (searchStore.hasSuggestions || searchStore.loading)
          "
          class="search-suggestions"
          @mousedown.prevent
        >
          <div v-if="searchStore.loading" class="suggestions-loading">搜索中...</div>
          <div v-else class="suggestions-list">
            <div
              v-for="(item, index) in searchStore.suggestions"
              :key="item.sid"
              class="suggestion-item"
              :class="{ 'suggestion-item--active': selectedIndex === index }"
              @mousedown="onSuggestionClick(item)"
            >
              <span class="suggestion-type-badge" :class="`suggestion-type--${item.type}`">
                {{ item.type }}
              </span>
              <div class="suggestion-content">
                <span class="suggestion-label">{{ item.label }}</span>
                <span class="suggestion-sublabel">{{ item.sublabel }}</span>
              </div>
            </div>
          </div>
        </div>
      </Transition>
    </div>

    <template #right>
      <!-- 整体组切换（mode="out-in" 避免双元素并发导致的 reflow 跳变） -->
      <Transition name="group-swap" mode="out-in">
        <div v-if="layoutMode === 'guest' && !isLoggedIn" key="logged-out" class="logged-out-group">
          <a :href="repoUrl" target="_blank" rel="noopener noreferrer" class="nav-item">加入我们</a>
          <RouterLink to="/login" class="nav-item login-btn">登录</RouterLink>
        </div>
        <div
          v-else-if="isLoggedIn && layoutMode === 'guest'"
          key="logged-in"
          class="logged-in-group"
        >
          <div class="user-menu-wrap">
            <ArAvatar
              v-bind="{
                ...(userStore.userInfo ? { username: userStore.userInfo.username } : {}),
                size: 30
              }"
              @click="showUserMenu = !showUserMenu"
            />
            <div v-if="showUserMenu" class="user-dropdown" @click="showUserMenu = false">
              <div class="dropdown-header">
                <ArAvatar
                  v-bind="{
                    ...(userStore.userInfo ? { username: userStore.userInfo.username } : {}),
                    size: 36
                  }"
                />
                <div class="dropdown-user-info">
                  <span class="dropdown-username">{{
                    userStore.userInfo?.username || '用户'
                  }}</span>
                </div>
              </div>
              <div class="dropdown-stats">
                <div class="stat-cell">
                  <span class="stat-num">--</span>
                  <span class="stat-label">帖子</span>
                </div>
                <div class="stat-cell">
                  <span class="stat-num">--</span>
                  <span class="stat-label">收藏</span>
                </div>
                <div class="stat-cell">
                  <span class="stat-num">--</span>
                  <span class="stat-label">积分</span>
                </div>
              </div>
              <div class="dropdown-divider"></div>
              <RouterLink to="/profile" class="dropdown-item">
                <NIcon size="16"><PersonOutline /></NIcon>
                <span>个人中心</span>
              </RouterLink>
              <RouterLink v-if="isAdmin" to="/console" class="dropdown-item">
                <NIcon size="16"><SettingsOutline /></NIcon>
                <span>控制台</span>
              </RouterLink>
              <div class="dropdown-divider"></div>
              <button class="dropdown-item logout-item" @click="handleLogout">
                <NIcon size="16"><LogOutOutline /></NIcon>
                <span>退出登录</span>
              </button>
            </div>
          </div>
          <RouterLink v-if="isAdmin" to="/console" class="nav-item console-btn">控制台</RouterLink>
        </div>
      </Transition>

      <!-- 其他布局模式下的用户菜单 -->
      <div v-if="layoutMode !== 'guest'" class="user-menu-wrap">
        <button class="user-info-btn" @click="showUserMenu = !showUserMenu" aria-label="用户菜单">
          <span class="username">{{ userStore.userInfo?.username || '用户' }}</span>
          <ArAvatar
            v-bind="{
              ...(userStore.userInfo ? { username: userStore.userInfo.username } : {}),
              size: 26
            }"
          />
        </button>
        <div v-if="showUserMenu" class="user-dropdown">
          <button v-if="layoutMode === 'user'" class="dropdown-item" @click="goToProfile">
            个人中心
          </button>
          <button v-if="layoutMode === 'admin'" class="dropdown-item" @click="goToHome">
            回到首页
          </button>
          <div class="dropdown-divider"></div>
          <button class="dropdown-item logout-item" @click="handleLogout">退出登录</button>
        </div>
      </div>
    </template>
  </ArTopNav>
</template>

<style>
/* ── Guest Mode: Nav Menu ── */
.nav-menu {
  display: flex;
  gap: var(--spacing-xs);
  align-items: center;
  flex-shrink: 0;
}

/* ── Menu Toggle ── */
.menu-toggle {
  width: 36px;
  height: 36px;
  border: none;
  background: var(--surface-color);
  border-radius: var(--radius-sm);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-secondary);
  transition: background-color var(--transition-fast);
}

.menu-toggle:hover {
  background: var(--surface-strong-color);
}

/* ── Search Section ── */
.search-section {
  position: relative;
  flex: 1;
  display: flex;
  justify-content: flex-end;
  min-width: 0;
}

.search-section--compact {
  max-width: 360px;
}

/* ── Search Wrap ── */
.search-wrap {
  position: relative;
  width: 100%;
  max-width: 480px;
}

.search-section--compact .search-wrap {
  max-width: 320px;
}

/* ── Search Input ── */
.search-input {
  width: 100%;
  height: 36px;
  border-radius: var(--radius-full);
  border: 1px solid var(--border-color);
  background: var(--bg-color);
  padding: 0 14px 0 36px;
  color: var(--text-primary);
  outline: none;
  font-size: 13px;
  transition:
    border-color var(--transition-fast),
    box-shadow var(--transition-fast);
}

.search-input:focus {
  border-color: var(--primary-color);
  box-shadow: 0 0 0 3px var(--primary-light-color);
  background: var(--surface-color);
}

/* ── Search Icon ── */
.search-leading-icon {
  position: absolute;
  left: 12px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--text-tertiary);
  pointer-events: none;
  z-index: 1;
}

.search-wrap:focus-within .search-leading-icon {
  color: var(--primary-color);
}

/* ── Search Loading ── */
.search-loading {
  position: absolute;
  right: 12px;
  top: 50%;
  transform: translateY(-50%);
  z-index: 2;
}

.loading-dot {
  display: block;
  width: 16px;
  height: 16px;
  border: 2px solid var(--border-color);
  border-top-color: var(--primary-color);
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

/* ── Suggestions Dropdown ── */
.search-suggestions {
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  right: 0;
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-lg);
  z-index: 300;
  max-height: 320px;
  overflow-y: auto;
}

.suggestions-loading {
  padding: 12px 14px;
  font-size: 13px;
  color: var(--text-tertiary);
  text-align: center;
}

.suggestions-list {
  display: flex;
  flex-direction: column;
}

.suggestion-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  cursor: pointer;
  transition: background var(--transition-fast);
}

.suggestion-item:hover,
.suggestion-item--active {
  background: var(--primary-light-color);
}

.suggestion-type-badge {
  flex-shrink: 0;
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  padding: 2px 6px;
  border-radius: var(--radius-sm);
  background: var(--surface-strong-color);
  color: var(--text-tertiary);
}

.suggestion-type--post {
  background: #e8f5e9;
  color: #2e7d32;
}

.suggestion-type--user {
  background: #e3f2fd;
  color: #1565c0;
}

.suggestion-type--file {
  background: #fff3e0;
  color: #e65100;
}

.suggestion-type--task {
  background: #f3e5f5;
  color: #6a1b9a;
}

.suggestion-type--log {
  background: #eceff1;
  color: #546e7a;
}

.suggestion-content {
  display: flex;
  flex-direction: column;
  min-width: 0;
  flex: 1;
}

.suggestion-label {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.suggestion-sublabel {
  font-size: 11px;
  color: var(--text-tertiary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* ── Suggestions enter/leave animation ── */
.suggestions-fade-enter-active,
.suggestions-fade-leave-active {
  transition:
    opacity 0.15s ease,
    transform 0.15s ease;
}

.suggestions-fade-enter-from,
.suggestions-fade-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

/* ── Nav Item ── */
.nav-item {
  color: var(--text-secondary);
  text-decoration: none;
  font-weight: var(--font-weight-medium);
  padding: 8px 14px;
  border-radius: var(--radius-md);
  transition: all var(--transition-fast);
  font-size: 14px;
  white-space: nowrap;
}

.nav-item:hover,
.nav-item.active {
  background: var(--primary-light-color);
  color: var(--primary-color);
}

.login-btn {
  background: var(--primary-color);
  color: #fff;
  border-radius: var(--radius-full);
  padding: 8px 18px;
}

.login-btn:hover {
  background: var(--primary-hover-color);
  color: #fff;
}

/* ── Breadcrumb ── */
.breadcrumb {
  font-size: 14px;
  color: var(--text-secondary);
  flex-shrink: 0;
}

.breadcrumb-sep {
  margin: 0 var(--spacing-sm);
  color: var(--text-tertiary);
}

/* ── 登录后组 ── */
.logged-in-group {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.logged-out-group {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
}

/* ── User Info Button (user/admin) ── */
.user-info-btn {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: 6px 10px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: background var(--transition-fast);
  border: none;
  background: transparent;
  color: inherit;
  font: inherit;
}

.user-info-btn:hover {
  background: var(--surface-strong-color);
}

.username {
  font-weight: var(--font-weight-medium);
  font-size: 14px;
  color: var(--text-secondary);
}

/* ── User Dropdown ── */
.user-menu-wrap {
  position: relative;
}

.user-dropdown {
  position: absolute;
  top: calc(100% + 6px);
  left: 50%;
  transform: translateX(-50%);
  min-width: 150px;
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-lg);
  z-index: 300;
  overflow: hidden;
}

.dropdown-item {
  display: block;
  width: 100%;
  padding: 9px 14px;
  font-size: 13px;
  color: var(--text-primary);
  text-decoration: none;
  background: none;
  border: none;
  text-align: left;
  cursor: pointer;
  transition: background var(--transition-fast);
  font-family: inherit;
}

.dropdown-item:hover {
  background: var(--primary-light-color);
  color: var(--primary-color);
}

.logout-item:hover {
  color: var(--error-color);
}

.dropdown-divider {
  height: 1px;
  background: var(--divider-color);
  margin: 4px 0;
}

/* ── Dropdown Header ── */
.dropdown-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 14px;
  border-bottom: 1px solid var(--divider-color);
}

.dropdown-user-info {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.dropdown-username {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

/* ── Dropdown Stats ── */
.dropdown-stats {
  display: flex;
  padding: 10px 14px;
  border-bottom: 1px solid var(--divider-color);
}

.stat-cell {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1px;
}

.stat-num {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-primary);
}

.stat-label {
  font-size: 10px;
  color: var(--text-tertiary);
}

/* ── Dropdown items with icons ── */
.dropdown-item {
  display: flex !important;
  align-items: center;
  gap: 8px;
}

/* ── Console Button ── */
.console-btn {
  color: var(--text-secondary);
  text-decoration: none;
  font-weight: var(--font-weight-medium);
  padding: 8px 14px;
  border-radius: var(--radius-md);
  transition: all var(--transition-fast);
  font-size: 14px;
  white-space: nowrap;
}

.console-btn:hover {
  background: var(--primary-light-color);
  color: var(--primary-color);
}

/* ── Responsive ── */
@media (max-width: 992px) {
  .search-section--compact .search-wrap {
    max-width: 240px;
  }
}

/* ════════════════════════════════════════
   登录转场动画
   ════════════════════════════════════════ */

.group-swap-leave-active {
  transition: all 0.3s ease;
}

.group-swap-leave-to {
  opacity: 0;
  transform: translateX(-15px);
}

.group-swap-enter-active {
  transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
}

.group-swap-enter-from {
  opacity: 0;
  transform: translateX(25px);
}
</style>
