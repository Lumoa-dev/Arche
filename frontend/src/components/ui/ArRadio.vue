<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    /** 当前选中的值（v-model） */
    modelValue?: string | number | boolean
    /** 此选项的值 */
    value?: string | number | boolean
    /** 标签文字 */
    label?: string
    /** 标签在圆点的哪一侧 */
    labelPosition?: 'left' | 'right'
    /** 是否禁用 */
    disabled?: boolean
  }>(),
  {
    modelValue: undefined,
    value: undefined,
    label: '',
    labelPosition: 'right',
    disabled: false
  }
)

const emit = defineEmits<{
  'update:modelValue': [value: string | number | boolean]
}>()

const checked = computed(() => props.modelValue === props.value)

const classes = computed(() => [
  'ar-radio',
  `ar-radio--${props.labelPosition}`,
  {
    'ar-radio--checked': checked.value,
    'ar-radio--disabled': props.disabled
  }
])

function handleClick() {
  if (props.disabled || checked.value || props.value === undefined) return
  emit('update:modelValue', props.value)
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === ' ' || e.key === 'Enter') {
    e.preventDefault()
    handleClick()
  }
}
</script>

<template>
  <div
    :class="classes"
    role="radio"
    :aria-checked="checked"
    :tabindex="disabled ? undefined : 0"
    @click="handleClick"
    @keydown="handleKeydown"
  >
    <label v-if="label && labelPosition === 'left'" class="ar-radio__label">{{ label }}</label>
    <span class="ar-radio__dot">
      <span class="ar-radio__fill" />
    </span>
    <label v-if="label && labelPosition === 'right'" class="ar-radio__label">{{ label }}</label>
  </div>
</template>

<style scoped>
.ar-radio {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  cursor: pointer;
  user-select: none;
  touch-action: manipulation;
  outline: none;
}

.ar-radio:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
  border-radius: var(--radius-sm);
}

.ar-radio--disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

/* ── label ── */
.ar-radio__label {
  font-family: var(--font-sans);
  font-size: var(--text-sm);
  color: var(--color-text-primary);
  line-height: 1;
  cursor: pointer;
}

.ar-radio--disabled .ar-radio__label {
  cursor: not-allowed;
}

/* ── 圆点外圈 ── */
.ar-radio__dot {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  border: 1.5px solid var(--color-border);
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.8);
  flex-shrink: 0;
  transition:
    border-color var(--transition-fast),
    background var(--transition-fast),
    box-shadow var(--transition-fast);
}

.ar-radio:hover:not(.ar-radio--disabled) .ar-radio__dot {
  border-color: var(--color-text-tertiary);
}

.ar-radio--checked .ar-radio__dot {
  border-color: var(--color-accent);
}

/* ── 内部填充圆 ── */
.ar-radio__fill {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--color-accent);
  transform: scale(0);
  transition: transform var(--transition-normal) var(--ease-out-spring);
}

.ar-radio--checked .ar-radio__fill {
  transform: scale(1);
}

/* ── label 在左 ── */
.ar-radio--left {
  flex-direction: row-reverse;
}
</style>
