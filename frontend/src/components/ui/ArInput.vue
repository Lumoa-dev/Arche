<script setup lang="ts">
import { computed, ref } from 'vue'

type InputSize = 'sm' | 'md' | 'lg'

const props = withDefaults(
  defineProps<{
    /** 标签文字（会自动追加冒号） */
    label?: string
    /** 双绑值 */
    modelValue?: string | number
    /** 原生 input type */
    type?: string
    /** 占位文字 */
    placeholder?: string
    /** 是否禁用 */
    disabled?: boolean
    /** 是否只读 */
    readonly?: boolean
    /** 错误信息（非空时进入错误状态） */
    error?: string
    /** 尺寸 */
    size?: InputSize
    /** 是否可清除 */
    clearable?: boolean
    /** 输入框名字 */
    name?: string
  }>(),
  {
    label: '',
    modelValue: '',
    type: 'text',
    placeholder: '',
    disabled: false,
    readonly: false,
    error: '',
    size: 'md',
    clearable: false,
    name: ''
  }
)

const emit = defineEmits<{
  'update:modelValue': [value: string]
  focus: [e: FocusEvent]
  blur: [e: FocusEvent]
  clear: []
}>()

const inputRef = ref<HTMLInputElement>()
const isFocused = ref(false)

const classes = computed(() => [
  'ar-input',
  `ar-input--${props.size}`,
  {
    'ar-input--disabled': props.disabled,
    'ar-input--error': !!props.error,
    'ar-input--focused': isFocused.value,
    'ar-input--has-label': !!props.label
  }
])

function handleInput(e: Event) {
  const value = (e.target as HTMLInputElement).value
  emit('update:modelValue', value)
}

function handleFocus(e: FocusEvent) {
  isFocused.value = true
  emit('focus', e)
}

function handleBlur(e: FocusEvent) {
  isFocused.value = false
  emit('blur', e)
}

function handleClear() {
  emit('update:modelValue', '')
  emit('clear')
  inputRef.value?.focus()
}
</script>

<template>
  <div :class="classes">
    <!-- 标签（带冒号） -->
    <label v-if="label" class="ar-input__label" :for="name">{{ label }}:</label>

    <!-- 输入区 — 纯下划线开放结构 -->
    <div class="ar-input__line">
      <input
        :id="name"
        ref="inputRef"
        :type="type"
        :value="modelValue"
        :placeholder="placeholder"
        :disabled="disabled"
        :readonly="readonly"
        :name="name"
        class="ar-input__field"
        @input="handleInput"
        @focus="handleFocus"
        @blur="handleBlur"
      />

      <!-- 清除按钮 -->
      <button
        v-if="clearable && !!modelValue && modelValue !== '' && !disabled"
        class="ar-input__clear"
        tabindex="-1"
        aria-label="清除"
        @click="handleClear"
        @mousedown.prevent
      >
        <svg
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2.5"
          stroke-linecap="round"
        >
          <line x1="18" y1="6" x2="6" y2="18" />
          <line x1="6" y1="6" x2="18" y2="18" />
        </svg>
      </button>
    </div>

    <!-- 错误信息 -->
    <p v-if="error" class="ar-input__error">{{ error }}</p>
  </div>
</template>

<style scoped>
/* ════════════════════════════════════════
   ArInput — 开放结构输入框
   设计意图：
   - 水平布局：Label:  +  下划线输入区
   - 底部线框，四边不围死（开放结构）
   - 聚焦时底线变色 + 微动画
   ════════════════════════════════════════ */

.ar-input {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--space-2);
  position: relative;
}

/* ── 标签 ── */
.ar-input__label {
  font-family: var(--font-sans);
  font-weight: var(--weight-medium);
  color: var(--color-text-secondary);
  white-space: nowrap;
  line-height: 1;
  flex-shrink: 0;
  transition: color var(--transition-fast);
  user-select: none;
}

/* ── 下划线输入区 ── */
.ar-input__line {
  position: relative;
  display: flex;
  align-items: center;
  flex: 1;
  min-width: 0;
  /* 下划线 */
  border-bottom: 1.5px solid var(--color-border);
  transition: border-color var(--transition-normal) var(--ease-out-smooth);
}

/* ── 原生输入框 ── */
.ar-input__field {
  flex: 1;
  min-width: 0;
  border: none;
  outline: none;
  background: transparent;
  font-family: var(--font-sans);
  color: var(--color-text-primary);
  line-height: 1.5;
  padding: 0;
}

.ar-input__field::placeholder {
  color: var(--color-text-quaternary);
}

/* ── 清除按钮 ── */
.ar-input__clear {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  border: none;
  background: transparent;
  color: var(--color-text-quaternary);
  cursor: pointer;
  border-radius: var(--radius-full);
  padding: 2px;
  transition:
    color var(--transition-fast),
    background var(--transition-fast);
}

.ar-input__clear:hover {
  color: var(--color-text-secondary);
  background: var(--color-bg-muted);
}

/* ── 错误信息 ── */
.ar-input__error {
  width: 100%;
  margin: 0;
  font-size: var(--text-xs);
  color: var(--color-danger);
  line-height: 1.4;
  padding-left: 2px;
}

/* ════════════════════════════════════════
   尺寸预设
   ════════════════════════════════════════ */

/* sm */
.ar-input--sm .ar-input__label {
  font-size: var(--text-xs);
}
.ar-input--sm .ar-input__line {
  padding-bottom: 2px;
}
.ar-input--sm .ar-input__field {
  font-size: var(--text-xs);
  min-height: 22px;
}
.ar-input--sm .ar-input__clear {
  width: 16px;
  height: 16px;
  margin-left: 2px;
}

/* md (default) */
.ar-input--md .ar-input__label {
  font-size: var(--text-sm);
}
.ar-input--md .ar-input__line {
  padding-bottom: 3px;
}
.ar-input--md .ar-input__field {
  font-size: var(--text-sm);
  min-height: 28px;
}
.ar-input--md .ar-input__clear {
  width: 18px;
  height: 18px;
  margin-left: var(--space-1);
}

/* lg */
.ar-input--lg .ar-input__label {
  font-size: var(--text-base);
}
.ar-input--lg .ar-input__line {
  padding-bottom: 4px;
}
.ar-input--lg .ar-input__field {
  font-size: var(--text-base);
  min-height: 32px;
}
.ar-input--lg .ar-input__clear {
  width: 20px;
  height: 20px;
  margin-left: var(--space-1);
}

/* ════════════════════════════════════════
   交互状态
   ════════════════════════════════════════ */

/* ── 聚焦 ── */
.ar-input--focused .ar-input__line {
  border-bottom-color: var(--color-accent);
  border-bottom-width: 1.5px;
}

.ar-input--focused .ar-input__label {
  color: var(--color-accent);
}

/* ── 错误 ── */
.ar-input--error .ar-input__line {
  border-bottom-color: var(--color-danger);
}

.ar-input--error .ar-input__label {
  color: var(--color-danger);
}

/* ── 禁用 ── */
.ar-input--disabled .ar-input__line {
  border-bottom-color: var(--color-border-light);
}

.ar-input--disabled .ar-input__field {
  color: var(--color-text-tertiary);
  cursor: not-allowed;
}

/* ── 悬停（非禁用非聚焦） ── */
.ar-input:not(.ar-input--disabled):not(.ar-input--focused) .ar-input__line:hover {
  border-bottom-color: var(--color-text-tertiary);
}
</style>
