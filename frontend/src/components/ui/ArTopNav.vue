<script setup lang="ts">
/**
 * ArTopNav — 顶部导航栏布局原语
 *
 * 纯布局组件，只关心结构和样式。
 * 所有内容通过 slot 注入，不接收任何业务数据。
 */
withDefaults(
  defineProps<{
    /** 布局变体，影响样式 */
    variant?: 'guest' | 'user' | 'admin'
    /** 是否显示侧边栏折叠按钮 */
    showMenuToggle?: boolean
  }>(),
  {
    variant: 'guest',
    showMenuToggle: false
  }
)

const emit = defineEmits<{
  toggleSidebar: []
}>()
</script>

<template>
  <header class="ar-top-nav" :class="`ar-top-nav--${variant}`">
    <!-- 左侧区域 -->
    <div class="ar-top-nav__left">
      <button
        v-if="showMenuToggle"
        class="ar-top-nav__toggle"
        @click="emit('toggleSidebar')"
        aria-label="切换侧边栏"
      >
        <svg
          width="20"
          height="20"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
        >
          <path d="M3 12h18M3 6h18M3 18h18" />
        </svg>
      </button>
      <slot name="left" />
    </div>

    <!-- 中间区域：默认撑满 flex 1 -->
    <div class="ar-top-nav__center">
      <slot />
    </div>

    <!-- 右侧区域 -->
    <div class="ar-top-nav__right">
      <slot name="right" />
    </div>
  </header>
</template>

<style scoped>
.ar-top-nav {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: 56px;
  display: flex;
  align-items: center;
  padding: 0 var(--content-padding);
  gap: var(--layout-gap);
  background: var(--surface-solid);
  border-bottom: 1px solid var(--border-color);
  z-index: 100;
}

/* ── Left ── */
.ar-top-nav__left {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  flex-shrink: 0;
}

.ar-top-nav__toggle {
  width: 36px;
  height: 36px;
  border: none;
  background: transparent;
  border-radius: var(--radius-sm);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-secondary);
  transition: background var(--transition-fast);
}

.ar-top-nav__toggle:hover {
  background: var(--surface-strong-color);
}

/* ── Center ── */
.ar-top-nav__center {
  display: flex;
  align-items: center;
  flex: 1;
  min-width: 0;
  gap: var(--spacing-md);
}

/* ── Right ── */
.ar-top-nav__right {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  flex-shrink: 0;
}
</style>
