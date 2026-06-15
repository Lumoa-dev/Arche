<script setup lang="ts">
import { computed } from 'vue'

type SelectSize = 'sm' | 'md' | 'lg'

interface SelectOption {
  label: string
  value: string | number
  disabled?: boolean
}

const props = withDefaults(
  defineProps<{
    /** 选项列表 */
    options?: SelectOption[]
    /** 双绑值 */
    modelValue?: string | number
    /** 占位文字 */
    placeholder?: string
    /** 是否禁用 */
    disabled?: boolean
    /** 尺寸 */
    size?: SelectSize
    /** 是否可清除 */
    clearable?: boolean
    /** 原生 name */
    name?: string
  }>(),
  {
    options: () => [],
    modelValue: '',
    placeholder: '请选择',
    disabled: false,
    size: 'md',
    clearable: false,
    name: ''
  }
)

const emit = defineEmits<{
  'update:modelValue': [value: string | number]
  change: [value: string | number]
}>()

const classes = computed(() => [
  'ar-select',
  `ar-select--${props.size}`,
  {
    'ar-select--disabled': props.disabled,
    'ar-select--has-value': props.modelValue !== '' && props.modelValue !== undefined
  }
])

function handleChange(e: Event) {
  const target = e.target as HTMLSelectElement
  const value = target.value
  emit('update:modelValue', value)
  emit('change', value)
}
</script>

<template>
  <div :class="classes">
    <div class="ar-select__wrapper">
      <select
        :value="modelValue"
        :disabled="disabled"
        :name="name"
        class="ar-select__native"
        @change="handleChange"
      >
        <option v-if="placeholder" value="" disabled hidden>
          {{ placeholder }}
        </option>
        <option v-for="opt in options" :key="opt.value" :value="opt.value" :disabled="opt.disabled">
          {{ opt.label }}
        </option>
      </select>

      <!-- 自定义下拉箭头 -->
      <span class="ar-select__arrow" aria-hidden="true">
        <svg
          width="12"
          height="12"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2.5"
          stroke-linecap="round"
        >
          <polyline points="6 9 12 15 18 9" />
        </svg>
      </span>
    </div>
  </div>
</template>

<style scoped>
/* ════════════════════════════════════════
   ArSelect — 下拉选择
   样式统一：圆角、配色、聚焦动画与 ArInput 一致
   ════════════════════════════════════════ */

.ar-select {
  display: inline-flex;
  min-width: 120px;
}

/* ── 包裹层（模拟边框） ── */
.ar-select__wrapper {
  position: relative;
  display: flex;
  align-items: center;
  width: 100%;
  border: 1.5px solid var(--color-border);
  border-radius: var(--radius-md);
  background: rgba(255, 255, 255, 0.6);
  transition:
    border-color var(--transition-normal) var(--ease-out-smooth),
    box-shadow var(--transition-normal) var(--ease-out-smooth),
    background var(--transition-normal) var(--ease-out-smooth);
  cursor: pointer;
}

.ar-select__wrapper:hover {
  border-color: var(--color-text-tertiary);
}

/* ── 原生 select ── */
.ar-select__native {
  flex: 1;
  min-width: 0;
  border: none;
  outline: none;
  background: transparent;
  font-family: var(--font-sans);
  color: var(--color-text-primary);
  cursor: pointer;
  appearance: none;
  -webkit-appearance: none;
  -moz-appearance: none;
  padding-right: var(--space-6);
  line-height: 1.5;
}

.ar-select__native:focus {
  outline: none;
}

.ar-select:focus-within .ar-select__wrapper {
  border-color: var(--color-accent);
  background: rgba(255, 255, 255, 0.9);
  box-shadow: 0 0 0 3px rgba(194, 70, 46, 0.1);
}

/* ── placeholder 样式 ── */
.ar-select__native option[disabled][hidden] {
  color: var(--color-text-quaternary);
}

/* ── 下拉箭头 ── */
.ar-select__arrow {
  position: absolute;
  right: var(--space-2);
  top: 50%;
  transform: translateY(-50%);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-text-quaternary);
  pointer-events: none;
  transition: color var(--transition-fast);
}

.ar-select:focus-within .ar-select__arrow {
  color: var(--color-accent);
}

/* ════════════════════════════════════════
   尺寸预设
   ════════════════════════════════════════ */

.ar-select--sm .ar-select__wrapper {
  min-height: 28px;
  padding: 0 var(--space-2);
}
.ar-select--sm .ar-select__native {
  font-size: var(--text-xs);
  padding: var(--space-1) 0;
}
.ar-select--sm .ar-select__arrow {
  right: var(--space-1);
}

.ar-select--md .ar-select__wrapper {
  min-height: 36px;
  padding: 0 var(--space-3);
}
.ar-select--md .ar-select__native {
  font-size: var(--text-sm);
  padding: var(--space-2) 0;
}

.ar-select--lg .ar-select__wrapper {
  min-height: 44px;
  padding: 0 var(--space-4);
}
.ar-select--lg .ar-select__native {
  font-size: var(--text-base);
  padding: var(--space-3) 0;
}

/* ── 禁用 ── */
.ar-select--disabled .ar-select__wrapper {
  background: var(--color-bg-muted);
  border-color: var(--color-border-light);
  cursor: not-allowed;
}

.ar-select--disabled .ar-select__native {
  color: var(--color-text-tertiary);
  cursor: not-allowed;
}
</style>
