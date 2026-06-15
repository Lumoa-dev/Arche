<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    modelValue?: boolean
    disabled?: boolean
    size?: 'sm' | 'md'
  }>(),
  {
    modelValue: false,
    disabled: false,
    size: 'md'
  }
)

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
}>()

const classes = computed(() => [
  'ar-checkbox',
  `ar-checkbox--${props.size}`,
  {
    'ar-checkbox--checked': props.modelValue,
    'ar-checkbox--disabled': props.disabled
  }
])

function toggle() {
  if (props.disabled) return
  emit('update:modelValue', !props.modelValue)
}
</script>

<template>
  <button
    :class="classes"
    role="checkbox"
    :aria-checked="modelValue"
    :disabled="disabled"
    type="button"
    @click="toggle"
  >
    <span class="ar-checkbox__box">
      <!-- 勾号 SVG — 通过变形实现 "嗖转" 动画 -->
      <svg
        class="ar-checkbox__check"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="3"
        stroke-linecap="round"
        stroke-linejoin="round"
      >
        <polyline points="20 6 9 17 4 12" />
      </svg>
    </span>
  </button>
</template>

<style scoped>
.ar-checkbox {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  border: none;
  background: none;
  cursor: pointer;
  outline: none;
  touch-action: manipulation;
  flex-shrink: 0;
}

.ar-checkbox:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
  border-radius: var(--radius-sm);
}

.ar-checkbox--disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

/* ── 方框 ── */
.ar-checkbox__box {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1.5px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: rgba(255, 255, 255, 0.8);
  transition:
    background var(--transition-fast),
    border-color var(--transition-fast),
    box-shadow var(--transition-fast);
}

.ar-checkbox:hover:not(.ar-checkbox--disabled) .ar-checkbox__box {
  border-color: var(--color-text-tertiary);
}

.ar-checkbox--checked .ar-checkbox__box {
  background: var(--color-accent);
  border-color: var(--color-accent);
}

.ar-checkbox--checked:hover:not(.ar-checkbox--disabled) .ar-checkbox__box {
  background: var(--color-accent-hover);
  border-color: var(--color-accent-hover);
}

/* ── 勾号 — 旋转 + 缩放动画 ── */
.ar-checkbox__check {
  color: #fff;
  opacity: 0;
  transform: scale(0) rotate(-45deg);
  transition:
    opacity var(--transition-normal) var(--ease-out-spring),
    transform var(--transition-normal) var(--ease-out-spring);
}

.ar-checkbox--checked .ar-checkbox__check {
  opacity: 1;
  transform: scale(1) rotate(0deg);
}

/* ── 尺寸 ── */
.ar-checkbox--sm .ar-checkbox__box {
  width: 16px;
  height: 16px;
}
.ar-checkbox--sm .ar-checkbox__check {
  width: 10px;
  height: 10px;
}

.ar-checkbox--md .ar-checkbox__box {
  width: 20px;
  height: 20px;
}
.ar-checkbox--md .ar-checkbox__check {
  width: 13px;
  height: 13px;
}
</style>
