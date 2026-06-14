<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import ArCheckbox from './ArCheckbox.vue'

export interface MultiSelectItem {
  id: string | number
  title: string
  selected?: boolean
  disabled?: boolean
}

const props = withDefaults(
  defineProps<{
    /** 选项列表 */
    items?: MultiSelectItem[]
    /** 已选中的 id 数组（双绑） */
    modelValue?: (string | number)[]
    /** item 高度（px），用于 3 项对齐计算 */
    itemSize?: number
    /** 是否禁用 */
    disabled?: boolean
    /** 对齐步数（点击箭头移动的 item 数） */
    step?: number
  }>(),
  {
    items: () => [],
    modelValue: () => [],
    itemSize: 42,
    disabled: false,
    step: 3
  }
)

const emit = defineEmits<{
  'update:modelValue': [value: (string | number)[]]
  'update:items': [items: MultiSelectItem[]]
  reorder: [items: MultiSelectItem[]]
}>()

// ─── DOM refs ───
const containerRef = ref<HTMLDivElement>()
const viewportRef = ref<HTMLDivElement>()
const innerRef = ref<HTMLDivElement>()
const itemRefs = ref<Map<number, HTMLElement>>(new Map())

// ─── 选中状态同步 ───
const localItems = ref<MultiSelectItem[]>([])

watch(() => props.items, (val) => {
  localItems.value = val.map(item => ({
    ...item,
    selected: props.modelValue.includes(item.id)
  }))
}, { immediate: true, deep: true })

function syncModelValue() {
  emit('update:modelValue', localItems.value.filter(i => i.selected).map(i => i.id))
}

// ─── 滚动物理引擎 ───
const SCROLL_FRICTION = 0.90
const MIN_VELOCITY = 0.5
const WHEEL_FACTOR = 0.5

let offset = ref(0)
let velocity = 0
let animFrameId: number | null = null
let isAnimating = false // 箭头按钮动画中

const maxOffset = computed(() => {
  if (!viewportRef.value || !innerRef.value) return 0
  const viewportH = viewportRef.value.clientHeight
  const innerH = innerRef.value.scrollHeight
  return Math.min(0, viewportH - innerH)
})

function clampOffset(to?: number) {
  if (to !== undefined) {
    offset.value = Math.max(maxOffset.value, Math.min(0, to))
  } else {
    offset.value = Math.max(maxOffset.value, Math.min(0, offset.value))
  }
}

// ─── 物理 tick ───
function physicsTick() {
  if (Math.abs(velocity) < MIN_VELOCITY) {
    velocity = 0
    stopPhysics()
    return
  }
  offset.value += velocity
  velocity *= SCROLL_FRICTION
  clampOffset()
  animFrameId = requestAnimationFrame(physicsTick)
}

function stopPhysics() {
  if (animFrameId) {
    cancelAnimationFrame(animFrameId)
    animFrameId = null
  }
}

// ─── 滚轮事件 ───
function onWheel(e: WheelEvent) {
  if (props.disabled || isAnimating) return
  // 检查是否还能滚动
  if ((e.deltaY > 0 && offset.value <= maxOffset.value) ||
      (e.deltaY < 0 && offset.value >= 0)) return
  velocity += e.deltaY * WHEEL_FACTOR
  if (!animFrameId) {
    animFrameId = requestAnimationFrame(physicsTick)
  }
}

// ─── 箭头按钮 ───
const showDownArrow = ref(false)
const showUpArrow = ref(false)

function updateArrowVisibility() {
  if (!viewportRef.value || !innerRef.value) return
  const viewH = viewportRef.value.clientHeight
  const innerH = innerRef.value.scrollHeight
  showDownArrow.value = innerH > viewH && offset.value > maxOffset.value - 1
  showUpArrow.value = innerH > viewH && offset.value < -1
}

watch([offset, maxOffset], () => {
  updateArrowVisibility()
})

// 箭头滚动 — 贝塞尔优雅降速
function scrollToNext() {
  if (isAnimating || !innerRef.value) return
  const currentIdx = Math.max(0, Math.round(-offset.value / props.itemSize))
  const targetIdx = Math.min(localItems.value.length - 1, currentIdx + props.step)
  const targetOffset = -(targetIdx * props.itemSize)
  animateTo(targetOffset)
}

function scrollToPrev() {
  if (isAnimating || !innerRef.value) return
  const currentIdx = Math.max(0, Math.round(-offset.value / props.itemSize))
  const targetIdx = Math.max(0, currentIdx - props.step)
  const targetOffset = -(targetIdx * props.itemSize)
  animateTo(targetOffset)
}

function animateTo(target: number) {
  if (!innerRef.value) return
  clampOffset(target)
  offset.value = target
}

// ─── 拖拽排序 ───
let dragIndex = ref<number | null>(null)
let dragOverIndex = ref<number | null>(null)

function onDragStart(_e: DragEvent, index: number) {
  dragIndex.value = index
}

function onDragOver(e: DragEvent, index: number) {
  e.preventDefault()
  dragOverIndex.value = index
}

function onDrop(_e: DragEvent, index: number) {
  if (dragIndex.value === null || dragIndex.value === index) {
    dragIndex.value = null
    dragOverIndex.value = null
    return
  }
  const items = [...localItems.value]
  const [moved] = items.splice(dragIndex.value, 1)
  items.splice(index, 0, moved)
  localItems.value = items
  emit('update:items', items)
  emit('reorder', items)
  dragIndex.value = null
  dragOverIndex.value = null
}

function onDragEnd() {
  dragIndex.value = null
  dragOverIndex.value = null
}

// ─── 选项勾选 ───
function onToggle(index: number, val: boolean) {
  if (props.disabled || localItems.value[index]?.disabled) return
  localItems.value[index].selected = val
  syncModelValue()
}

// ─── 暴露的 API ───
function refresh() {
  nextTick(() => {
    clampOffset()
    updateArrowVisibility()
  })
}

function selectAll() {
  localItems.value.forEach(i => { if (!i.disabled) i.selected = true })
  syncModelValue()
}

function clearAll() {
  localItems.value.forEach(i => { i.selected = false })
  syncModelValue()
}

defineExpose({ refresh, selectAll, clearAll })

// ─── 生命周期 ───
onMounted(() => {
  refresh()
})

onUnmounted(() => {
  stopPhysics()
})

// 窗口 resize 时更新
watch(() => [props.items, props.modelValue], () => {
  nextTick(refresh)
}, { deep: true })
</script>

<template>
  <div class="ar-multi-select" :class="{ 'ar-multi-select--disabled': disabled }" ref="containerRef">
    <div class="ar-multi-select__viewport" ref="viewportRef" @wheel.prevent="onWheel">
      <div class="ar-multi-select__inner" ref="innerRef" :style="{ transform: `translateY(${offset}px)` }">
        <div
          v-for="(item, index) in localItems"
          :key="item.id"
          :ref="el => { if (el) itemRefs.set(index, el as HTMLElement) }"
          class="ar-multi-select__item"
          :class="{
            'ar-multi-select__item--checked': item.selected,
            'ar-multi-select__item--disabled': item.disabled,
            'ar-multi-select__item--dragging': dragIndex === index,
            'ar-multi-select__item--drag-over': dragOverIndex === index && dragIndex !== null
          }"
          :draggable="!disabled && !item.disabled"
          @dragstart="onDragStart($event, index)"
          @dragover="onDragOver($event, index)"
          @drop="onDrop($event, index)"
          @dragend="onDragEnd"
        >
          <span class="ar-multi-select__title">{{ item.title }}</span>
          <ArCheckbox
            :model-value="!!item.selected"
            :disabled="disabled || item.disabled"
            size="sm"
            @update:model-value="onToggle(index, $event)"
          />
        </div>
      </div>
    </div>

    <!-- 向下箭头 -->
    <Transition name="ar-arrow-fade">
      <button
        v-if="showDownArrow && !disabled"
        class="ar-multi-select__arrow ar-multi-select__arrow--down"
        title="下移三项"
        @click="scrollToNext"
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round">
          <polyline points="6 9 12 15 18 9" />
        </svg>
      </button>
    </Transition>

    <!-- 向上箭头 -->
    <Transition name="ar-arrow-fade">
      <button
        v-if="showUpArrow && !disabled"
        class="ar-multi-select__arrow ar-multi-select__arrow--up"
        title="上移三项"
        @click="scrollToPrev"
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round">
          <polyline points="18 15 12 9 6 15" />
        </svg>
      </button>
    </Transition>
  </div>
</template>

<style scoped>
/* ════════════════════════════════════════
   ArMultiSelect — 组合多选容器
   - 标题左 + 复选框右
   - 惯性滚轮滚动
   - 箭头按钮 + 贝塞尔对齐
   - HTML5 拖拽排序
   - 永远不显示滚动条
   ════════════════════════════════════════ */

.ar-multi-select {
  position: relative;
  border: 1.5px solid var(--color-border);
  border-radius: var(--radius-md);
  background: rgba(255, 255, 255, 0.6);
  overflow: hidden;
  transition:
    border-color var(--transition-normal),
    box-shadow var(--transition-normal);
}

.ar-multi-select:focus-within {
  border-color: var(--color-accent);
  box-shadow: 0 0 0 3px rgba(194, 70, 46, 0.1);
}

.ar-multi-select--disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* ── 视口（隐藏滚动条） ── */
.ar-multi-select__viewport {
  overflow: hidden;
  max-height: 280px;
  scrollbar-width: none;
  -ms-overflow-style: none;
}

.ar-multi-select__viewport::-webkit-scrollbar {
  display: none;
}

/* ── 内层（偏移用） ── */
.ar-multi-select__inner {
  will-change: transform;
}

/* ── 单个 item ── */
.ar-multi-select__item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: v-bind('props.itemSize + "px"');
  padding: 0 var(--space-3);
  cursor: pointer;
  user-select: none;
  transition:
    background var(--transition-fast),
    opacity var(--transition-fast);
  /* 左右不靠已有 padding */
  /* 上下紧凑: border-bottom 间隔 */
}

.ar-multi-select__item + .ar-multi-select__item {
  border-top: 1px solid var(--color-border-light);
}

.ar-multi-select__item:hover {
  background: var(--color-bg-soft);
}

/* 选中底色 */
.ar-multi-select__item--checked {
  background: rgba(194, 70, 46, 0.04);
}

.ar-multi-select__item--checked:hover {
  background: rgba(194, 70, 46, 0.08);
}

/* 禁用 */
.ar-multi-select__item--disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

/* 拖拽中 */
.ar-multi-select__item--dragging {
  opacity: 0.4;
}

/* 拖拽悬停目标 */
.ar-multi-select__item--drag-over {
  border-top-color: var(--color-accent) !important;
  background: rgba(194, 70, 46, 0.06);
}

/* ── 标题 ── */
.ar-multi-select__title {
  font-family: var(--font-sans);
  font-size: var(--text-sm);
  color: var(--color-text-primary);
  line-height: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1;
  min-width: 0;
  padding-right: var(--space-2);
}

/* ── 箭头按钮 ── */
.ar-multi-select__arrow {
  position: absolute;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: 1.5px solid var(--color-border);
  border-radius: 50%;
  background: var(--color-bg-surface);
  color: var(--color-text-tertiary);
  cursor: pointer;
  box-shadow: var(--shadow-sm);
  transition:
    background var(--transition-fast),
    color var(--transition-fast),
    border-color var(--transition-fast),
    box-shadow var(--transition-fast);
  z-index: 2;
}

.ar-multi-select__arrow:hover {
  background: var(--color-bg-soft);
  color: var(--color-accent);
  border-color: var(--color-accent);
  box-shadow: var(--shadow-md);
}

.ar-multi-select__arrow--down {
  bottom: var(--space-2);
  left: 50%;
  transform: translateX(-50%);
}

.ar-multi-select__arrow--up {
  top: var(--space-2);
  left: 50%;
  transform: translateX(-50%);
}

/* ── 箭头淡入淡出 ── */
.ar-arrow-fade-enter-active,
.ar-arrow-fade-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.ar-arrow-fade-enter-from {
  opacity: 0;
  transform: translateX(-50%) scale(0.8);
}

.ar-arrow-fade-leave-to {
  opacity: 0;
  transform: translateX(-50%) scale(0.8);
}
</style>
