<script setup lang="ts">
import { computed } from 'vue'

type ButtonType = 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger'
type ButtonSize = 'sm' | 'md' | 'lg'

const props = withDefaults(
  defineProps<{
    type?: ButtonType
    size?: ButtonSize
    loading?: boolean
    disabled?: boolean
    icon?: boolean
  }>(),
  {
    type: 'secondary',
    size: 'md',
    loading: false,
    disabled: false,
    icon: false
  }
)

const emit = defineEmits<{
  click: [e: MouseEvent]
}>()

const classes = computed(() => [
  'ar-button',
  `ar-button--${props.type}`,
  `ar-button--${props.size}`,
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
    box-shadow var(--transition-normal),
    transform var(--transition-normal);
  user-select: none;
  -webkit-user-select: none;
  touch-action: manipulation;
}

.ar-button:hover:not(.is-disabled) {
  transform: translateY(-1px);
}

.ar-button:active:not(.is-disabled) {
  transform: translateY(0);
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

/* ── icon mode ── */
.ar-button--icon {
  padding: 0;
}

/* ── sizes ── */
.ar-button--sm {
  height: 28px;
  font-size: 12px;
  border-radius: var(--radius-sm);
  padding: 0 10px;
}
.ar-button--sm.ar-button--icon {
  width: 28px;
}

.ar-button--md {
  height: 36px;
  font-size: 14px;
  border-radius: var(--radius-md);
  padding: 0 16px;
}
.ar-button--md.ar-button--icon {
  width: 36px;
}

.ar-button--lg {
  height: 44px;
  font-size: 16px;
  border-radius: var(--radius-md);
  padding: 0 24px;
}
.ar-button--lg.ar-button--icon {
  width: 44px;
}

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
  background-color: var(--primary-light-color);
  color: var(--text-primary);
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

/* ── spinner ── */
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
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

/* ── icon slot ── */
.ar-button__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
</style>
