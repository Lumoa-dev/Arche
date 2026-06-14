<script setup lang="ts">
/**
 * ArButton — 通用按钮
 *
 * 规格系统：
 * - 尺寸（size）：xs(22px) / sm(28px) / md(36px) / lg(44px)
 * - 形状（shape）：rect(长方形) / square(正方形) / pill(胶囊)
 * - 变体（type）：primary / secondary / outline / ghost / danger
 *
 * 纯图标按钮：设 icon=true + 用 #icon 插槽传 SVG，
 * 图标尺寸会被按钮自动约束到当前尺寸的对应规格。
 */

import { computed } from 'vue'

type ButtonType = 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger'
type ButtonSize = 'xs' | 'sm' | 'md' | 'lg'
type ButtonShape = 'rect' | 'square' | 'pill'

const props = withDefaults(
  defineProps<{
    type?: ButtonType
    size?: ButtonSize
    /** 形状；rect=长方形 square=正方形 pill=胶囊 */
    shape?: ButtonShape
    /** 是否纯图标按钮（无文字），会自动 square */
    icon?: boolean
    loading?: boolean
    disabled?: boolean
  }>(),
  {
    type: 'secondary',
    size: 'md',
    shape: 'rect',
    icon: false,
    loading: false,
    disabled: false
  }
)

const emit = defineEmits<{
  click: [e: MouseEvent]
}>()

const classes = computed(() => [
  'ar-button',
  `ar-button--${props.type}`,
  `ar-button--${props.size}`,
  // 纯图标按钮强制方型
  props.icon || props.shape === 'square'
    ? 'ar-button--square'
    : `ar-button--${props.shape}`,
  {
    'ar-button--icon': props.icon,
    'ar-button--loading': props.loading,
    'is-disabled': props.disabled
  }
])

function handleClick(e: MouseEvent) {
  if (props.loading || props.disabled) return
  emit('click', e)
}
</script>

<template>
  <button
    :class="classes"
    :disabled="disabled || loading"
    :aria-disabled="disabled || loading"
    @click="handleClick"
  >
    <span v-if="loading" class="ar-button__spinner" aria-hidden="true">
      <svg viewBox="0 0 24 24" class="spinner-icon">
        <circle
          cx="12"
          cy="12"
          r="10"
          fill="none"
          stroke="currentColor"
          stroke-width="3"
          stroke-linecap="round"
          stroke-dasharray="31.4 31.4"
        />
      </svg>
    </span>
    <span v-if="$slots.icon" class="ar-button__icon">
      <slot name="icon" />
    </span>
    <span v-if="$slots.default && !icon" class="ar-button__text">
      <slot />
    </span>
  </button>
</template>

<style scoped>
/* ════════════════════════════════════════
   ArButton — 按钮系统
   设计原则：
   - 悬停不上弹（扁平）
   - ghost 悬停用中性灰而非品牌色
   - 圆角统一按尺寸定级
   - 图标按钮自动约束图标尺寸
   ════════════════════════════════════════ */

.ar-button {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  border: 1px solid transparent;
  cursor: pointer;
  font-family: var(--font-sans);
  font-weight: var(--font-weight-medium);
  line-height: 1;
  white-space: nowrap;
  outline: none;
  transition:
    background-color var(--transition-normal),
    border-color var(--transition-normal),
    color var(--transition-normal),
    box-shadow var(--transition-normal);
  user-select: none;
  -webkit-user-select: none;
  touch-action: manipulation;
  flex-shrink: 0;
}

.ar-button:focus-visible {
  outline: 2px solid var(--primary-color);
  outline-offset: 2px;
}

/* ── disabled ── */
.is-disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* ════════════════════════════════════════
   尺寸 & 圆角
   ════════════════════════════════════════ */

/* xs */
.ar-button--xs {
  height: 22px;
  font-size: 11px;
  border-radius: 4px;
  padding: 0 8px;
}
.ar-button--xs .ar-button__icon {
  width: 14px;
  height: 14px;
}

/* sm */
.ar-button--sm {
  height: 28px;
  font-size: 12px;
  border-radius: 6px;
  padding: 0 10px;
}
.ar-button--sm .ar-button__icon {
  width: 16px;
  height: 16px;
}

/* md */
.ar-button--md {
  height: 36px;
  font-size: 14px;
  border-radius: 10px;
  padding: 0 16px;
}
.ar-button--md .ar-button__icon {
  width: 20px;
  height: 20px;
}

/* lg */
.ar-button--lg {
  height: 44px;
  font-size: 16px;
  border-radius: 16px;
  padding: 0 24px;
}
.ar-button--lg .ar-button__icon {
  width: 24px;
  height: 24px;
}

/* ════════════════════════════════════════
   形状 — square（正方形）
   不设尺寸，字号决定内边距
   ════════════════════════════════════════ */
.ar-button--square {
  padding: 0;
  aspect-ratio: 1;
}

/* pill 用大圆角 */
.ar-button--pill {
  border-radius: 9999px;
}

/* ════════════════════════════════════════
   图标约束 — 强制 SVG 填满容器
   ════════════════════════════════════════ */
.ar-button--icon {
  /* icon mode overrides padding from size */
}

.ar-button__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

/* 穿透 slot：强制 SVG 按容器尺寸渲染 */
.ar-button__icon :deep(svg) {
  width: 100% !important;
  height: 100% !important;
  max-width: 100%;
  max-height: 100%;
}

/* ════════════════════════════════════════
   变体
   ════════════════════════════════════════ */

/* ── primary ── */
.ar-button--primary {
  background-color: var(--primary-color);
  color: #fff;
  border-color: var(--primary-color);
}
.ar-button--primary:hover:not(.is-disabled) {
  background-color: var(--primary-hover-color);
  border-color: var(--primary-hover-color);
  box-shadow: var(--shadow-md);
}
.ar-button--primary:active:not(.is-disabled) {
  background-color: var(--primary-pressed-color);
  border-color: var(--primary-pressed-color);
}

/* ── secondary ── */
.ar-button--secondary {
  background-color: var(--surface-color);
  color: var(--text-primary);
  border-color: var(--border-color);
}
.ar-button--secondary:hover:not(.is-disabled) {
  background-color: var(--surface-strong-color);
  border-color: var(--border-color);
  box-shadow: var(--shadow-sm);
}

/* ── outline ── */
.ar-button--outline {
  background-color: transparent;
  color: var(--primary-color);
  border-color: var(--primary-color);
}
.ar-button--outline:hover:not(.is-disabled) {
  background-color: var(--primary-light-color);
  box-shadow: var(--shadow-sm);
}
.ar-button--outline:active:not(.is-disabled) {
  background-color: rgba(58, 90, 74, 0.2);
}

/* ── ghost ── */
.ar-button--ghost {
  background-color: transparent;
  color: var(--text-secondary);
  border-color: transparent;
}
.ar-button--ghost:hover:not(.is-disabled) {
  background-color: rgba(0, 0, 0, 0.06);
  color: var(--text-primary);
}
.ar-button--ghost:active:not(.is-disabled) {
  background-color: rgba(0, 0, 0, 0.1);
}

/* ── danger ── */
.ar-button--danger {
  background-color: var(--color-danger);
  color: var(--color-text-on-primary);
  border-color: var(--color-danger);
}
.ar-button--danger:hover:not(.is-disabled) {
  background-color: #c43a3a;
  border-color: #c43a3a;
  box-shadow: var(--shadow-md);
}
.ar-button--danger:active:not(.is-disabled) {
  background-color: #a82e20;
  border-color: #a82e20;
}

/* ════════════════════════════════════════
   spinner
   ════════════════════════════════════════ */
.ar-button__spinner {
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.spinner-icon {
  width: 16px;
  height: 16px;
  animation: ar-spin 0.8s linear infinite;
}

@keyframes ar-spin {
  from { transform: rotate(0deg); }
  to   { transform: rotate(360deg); }
}
</style>
