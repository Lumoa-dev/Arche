<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import ArButton from '@/components/ui/ArButton.vue'

type ButtonType = 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger'
type PopconfirmPlacement = 'top' | 'bottom'

const props = withDefaults(
  defineProps<{
    title?: string
    content?: string
    positiveText?: string
    negativeText?: string
    positiveType?: ButtonType
    negativeType?: ButtonType
    placement?: PopconfirmPlacement
    width?: string | number
    disabled?: boolean
  }>(),
  {
    title: '确认操作',
    content: '',
    positiveText: '确认',
    negativeText: '取消',
    positiveType: 'primary',
    negativeType: 'ghost',
    placement: 'top',
    width: 240,
    disabled: false
  }
)

const emit = defineEmits<{
  'positive-click': []
  'negative-click': []
}>()

const visible = ref(false)
const wrapperRef = ref<HTMLElement | null>(null)

function toggle() {
  if (props.disabled) return
  visible.value = !visible.value
  if (visible.value) {
    nextTick(() => {
      wrapperRef.value?.focus()
    })
  }
}

function hide() {
  visible.value = false
}

function handlePositive() {
  emit('positive-click')
  hide()
}

function handleNegative() {
  emit('negative-click')
  hide()
}

function handleClickOutside(e: MouseEvent) {
  if (!visible.value) return
  if (wrapperRef.value && !wrapperRef.value.contains(e.target as Node)) {
    hide()
  }
}

function handleEscape(e: KeyboardEvent) {
  if (e.key === 'Escape' && visible.value) {
    hide()
  }
}

const popupStyle = computed(() => ({
  width: typeof props.width === 'number' ? `${props.width}px` : props.width
}))

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
  document.addEventListener('keydown', handleEscape)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
  document.removeEventListener('keydown', handleEscape)
})
</script>

<template>
  <div ref="wrapperRef" class="ar-popconfirm" tabindex="-1" @click.stop="toggle">
    <div class="ar-popconfirm__trigger">
      <slot name="trigger" />
    </div>
    <Transition name="ar-popconfirm-fade">
      <div
        v-if="visible"
        class="ar-popconfirm__popup"
        :class="`ar-popconfirm--${placement}`"
        :style="popupStyle"
        @click.stop
      >
        <div class="ar-popconfirm__arrow" />
        <div class="ar-popconfirm__body">
          <div class="ar-popconfirm__header">
            <slot name="title">
              <span class="ar-popconfirm__title">{{ title }}</span>
            </slot>
          </div>
          <div v-if="content || $slots.default" class="ar-popconfirm__content">
            <slot>{{ content }}</slot>
          </div>
          <div class="ar-popconfirm__actions">
            <slot name="action">
              <ArButton :type="negativeType" size="sm" @click="handleNegative">
                {{ negativeText }}
              </ArButton>
              <ArButton :type="positiveType" size="sm" @click="handlePositive">
                {{ positiveText }}
              </ArButton>
            </slot>
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.ar-popconfirm {
  position: relative;
  display: inline-flex;
  outline: none;
}

.ar-popconfirm__trigger {
  display: inline-flex;
}

.ar-popconfirm__popup {
  position: absolute;
  z-index: 2000;
  left: 50%;
  transform: translateX(-50%);
  background: var(--surface-color);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-lg);
  padding: 12px;
  min-width: 160px;
}

.ar-popconfirm--top {
  bottom: calc(100% + 10px);
}

.ar-popconfirm--bottom {
  top: calc(100% + 10px);
}

.ar-popconfirm__arrow {
  position: absolute;
  left: 50%;
  margin-left: -5px;
  width: 10px;
  height: 10px;
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  transform: translateX(-50%) rotate(45deg);
  z-index: -1;
}

.ar-popconfirm--top .ar-popconfirm__arrow {
  bottom: -6px;
  border-top: none;
  border-left: none;
}

.ar-popconfirm--bottom .ar-popconfirm__arrow {
  top: -6px;
  border-bottom: none;
  border-right: none;
}

.ar-popconfirm__body {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.ar-popconfirm__header {
  display: flex;
  align-items: center;
}

.ar-popconfirm__title {
  font-size: 14px;
  font-weight: var(--font-weight-semibold);
  color: var(--text-primary);
  line-height: 1.4;
}

.ar-popconfirm__content {
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.5;
  word-break: break-word;
}

.ar-popconfirm__actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 4px;
}

.ar-popconfirm-fade-enter-active,
.ar-popconfirm-fade-leave-active {
  transition:
    opacity 0.2s var(--ease-out-smooth),
    transform 0.2s var(--ease-out-smooth);
}

.ar-popconfirm-fade-enter-from,
.ar-popconfirm-fade-leave-to {
  opacity: 0;
}

.ar-popconfirm--top.ar-popconfirm-fade-enter-from,
.ar-popconfirm--top.ar-popconfirm-fade-leave-to {
  transform: translateX(-50%) translateY(4px);
}

.ar-popconfirm--bottom.ar-popconfirm-fade-enter-from,
.ar-popconfirm--bottom.ar-popconfirm-fade-leave-to {
  transform: translateX(-50%) translateY(-4px);
}
</style>
