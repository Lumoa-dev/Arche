<script setup lang="ts">
import { computed } from 'vue'

type SwitchSize = 'sm' | 'md'

const props = withDefaults(
  defineProps<{
    /** 双绑值 */
    modelValue?: boolean
    /** 是否禁用 */
    disabled?: boolean
    /** 尺寸 */
    size?: SwitchSize
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

const isOn = computed(() => props.modelValue)

const classes = computed(() => [
  'ar-switch',
  `ar-switch--${props.size}`,
  {
    'ar-switch--on': isOn.value,
    'ar-switch--off': !isOn.value,
    'ar-switch--disabled': props.disabled
  }
])

function toggle() {
  if (props.disabled) return
  emit('update:modelValue', !isOn.value)
}
</script>

<template>
  <button
    :class="classes"
    role="switch"
    :aria-checked="isOn"
    :disabled="disabled"
    type="button"
    @click="toggle"
  >
    <span class="ar-switch__track">
      <!-- 开/关文字 — 与圆球位置交叉排列 -->
      <span class="ar-switch__text ar-switch__text--on">开</span>
      <span class="ar-switch__text ar-switch__text--off">关</span>
      <!-- 滑动圆球 -->
      <span class="ar-switch__knob" />
    </span>
  </button>
</template>

<style scoped>
/* ════════════════════════════════════════
   ArSwitch — 滑动开关
   设计意图：圆球滑动 + 轨道剩余空间显示开/关文字
   ════════════════════════════════════════ */

.ar-switch {
  display: inline-flex;
  align-items: center;
  padding: 0;
  border: none;
  background: none;
  cursor: pointer;
  outline: none;
  touch-action: manipulation;
}

.ar-switch:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
  border-radius: var(--radius-full);
}

.ar-switch--disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* ── 轨道 ── */
.ar-switch__track {
  position: relative;
  display: flex;
  align-items: center;
  border-radius: var(--radius-full);
  transition: background var(--transition-normal) var(--ease-out-smooth);
  overflow: hidden;
  flex-shrink: 0;
}

/* ── 开/关文字 ── */
.ar-switch__text {
  position: absolute;
  font-family: var(--font-sans);
  font-weight: var(--weight-medium);
  line-height: 1;
  color: var(--color-text-on-primary);
  user-select: none;
  pointer-events: none;
  transition: opacity var(--transition-fast);
}

.ar-switch__text--on {
  opacity: 0;
}

.ar-switch__text--off {
  opacity: 1;
}

.ar-switch--on .ar-switch__text--on {
  opacity: 1;
}

.ar-switch--on .ar-switch__text--off {
  opacity: 0;
}

/* ── 圆球 ── */
.ar-switch__knob {
  position: absolute;
  border-radius: 50%;
  background: #fff;
  box-shadow:
    0 1px 3px rgba(0, 0, 0, 0.15),
    0 1px 2px rgba(0, 0, 0, 0.1);
  transition:
    transform var(--transition-slow) var(--ease-out-spring);
  z-index: 1;
}

/* ════════════════════════════════════════
   尺寸: md（默认）
   ════════════════════════════════════════ */
.ar-switch--md .ar-switch__track {
  width: 48px;
  height: 26px;
  padding: 0 10px;
  background: var(--color-text-quaternary);
}

.ar-switch--md.ar-switch--on .ar-switch__track {
  background: var(--color-accent);
}

.ar-switch--md .ar-switch__text {
  font-size: var(--text-xs);
}

.ar-switch--md .ar-switch__text--on {
  left: 8px;
}

.ar-switch--md .ar-switch__text--off {
  right: 8px;
}

.ar-switch--md .ar-switch__knob {
  width: 20px;
  height: 20px;
  top: 3px;
  left: 3px;
}

.ar-switch--md.ar-switch--on .ar-switch__knob {
  transform: translateX(22px);
}

/* ════════════════════════════════════════
   尺寸: sm
   ════════════════════════════════════════ */
.ar-switch--sm .ar-switch__track {
  width: 38px;
  height: 20px;
  padding: 0 7px;
  background: var(--color-text-quaternary);
}

.ar-switch--sm.ar-switch--on .ar-switch__track {
  background: var(--color-accent);
}

.ar-switch--sm .ar-switch__text {
  font-size: 9px;
}

.ar-switch--sm .ar-switch__text--on {
  left: 6px;
}

.ar-switch--sm .ar-switch__text--off {
  right: 6px;
}

.ar-switch--sm .ar-switch__knob {
  width: 16px;
  height: 16px;
  top: 2px;
  left: 2px;
}

.ar-switch--sm.ar-switch--on .ar-switch__knob {
  transform: translateX(18px);
}
</style>
