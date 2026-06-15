<script setup lang="ts">
/**
 * ArPage — 页面容器
 *
 * 纯粹的页面外壳，不包含任何布局逻辑。
 * 职责仅限于：
 *   - 提供统一的内边距和最大宽度
 *   - 管理页面级 loading / empty 状态
 *   - 提供滚动容器
 *
 * 内部的元素排列交给 ArHBox / ArVBox / ArGrid 等布局组件。
 */
withDefaults(
  defineProps<{
    /** 内边距（使用项目 spacing token 或任意 CSS 长度） */
    padding?: string
    /** 最大宽度 */
    maxWidth?: string
    /** 是否处于加载状态（显示加载中） */
    loading?: boolean
    /** 加载状态文案 */
    loadingText?: string
    /** 是否空状态 */
    empty?: boolean
    /** 空状态文案 */
    emptyText?: string
    /** 空状态图标 */
    emptyIcon?: string
  }>(),
  {
    padding: '',
    maxWidth: '',
    loading: false,
    loadingText: '加载中…',
    empty: false,
    emptyText: '暂无数据',
    emptyIcon: '📭'
  }
)

defineSlots<{
  default: void
  /** 自定义加载状态 */
  loading?: void
  /** 自定义空状态 */
  empty?: void
}>()
</script>

<template>
  <div
    class="ar-page"
    :style="{
      padding: padding || undefined,
      maxWidth: maxWidth || undefined
    }"
  >
    <!-- loading 态 -->
    <div v-if="loading" class="ar-page__loading">
      <slot name="loading">
        <div class="ar-page__loading-indicator">
          <span class="ar-page__spinner" />
          <span class="ar-page__loading-text">{{ loadingText }}</span>
        </div>
      </slot>
    </div>

    <!-- empty 态 -->
    <div v-else-if="empty" class="ar-page__empty">
      <slot name="empty">
        <div class="ar-page__empty-content">
          <span class="ar-page__empty-icon">{{ emptyIcon }}</span>
          <span class="ar-page__empty-text">{{ emptyText }}</span>
        </div>
      </slot>
    </div>

    <!-- 正常内容 -->
    <slot v-else />
  </div>
</template>

<style scoped>
.ar-page {
  display: block;
  width: 100%;
  min-height: 100%;
  box-sizing: border-box;
}

/* ── loading ── */
.ar-page__loading {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 240px;
}

.ar-page__loading-indicator {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--spacing-md);
}

.ar-page__spinner {
  width: 28px;
  height: 28px;
  border: 3px solid var(--color-border-light);
  border-top-color: var(--color-accent);
  border-radius: 50%;
  animation: ar-page-spin 0.7s linear infinite;
}

@keyframes ar-page-spin {
  to {
    transform: rotate(360deg);
  }
}

.ar-page__loading-text {
  font-size: 14px;
  color: var(--color-text-tertiary);
}

/* ── empty ── */
.ar-page__empty {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 240px;
}

.ar-page__empty-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--spacing-sm);
}

.ar-page__empty-icon {
  font-size: 40px;
  line-height: 1;
}

.ar-page__empty-text {
  font-size: 14px;
  color: var(--color-text-tertiary);
}
</style>
