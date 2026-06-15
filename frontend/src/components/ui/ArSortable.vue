<script setup lang="ts">
/**
 * ArSortable — 拖拽排序基础组件
 *
 * 纯 JS 实现拖拽排序，不依赖 vuedraggable / SortableJS。
 * 支持 X / Y / XY 轴约束，自定义手柄、幽灵样式、让位动画。
 *
 * 用法：
 *   <ArSortable v-model="items" axis="y" handle=".drag-handle">
 *     <template #item="{ element, index }">
 *       <MyCard :data="element" />
 *     </template>
 *   </ArSortable>
 *
 * 自定义幽灵：
 *   <template #ghost="{ index }">
 *     <div class="my-ghost">插入到第 {{ index }} 项</div>
 *   </template>
 */
import { ref, reactive } from 'vue'

type Axis = 'x' | 'y' | 'xy'
type GhostPreset = 'line' | 'box' | 'none'
// eslint-disable-next-line no-unused-vars
type ItemKeyFn = (item: any, index: number) => string | number

const props = withDefaults(
  defineProps<{
    modelValue: any[]
    axis?: Axis
    /** CSS 选择器：只有此选择器匹配的元素可抓起拖拽 */
    handle?: string
    /** 让位动画时长，ms */
    animation?: number
    /** 幽灵预设样式（#ghost 插槽优先级更高） */
    ghost?: GhostPreset
    /** 列表项 key 的字段名或函数 */
    itemKey?: string | ItemKeyFn
  }>(),
  {
    axis: 'y',
    animation: 150,
    ghost: 'line'
  }
)

const emit = defineEmits<{
  'update:modelValue': [value: any[]]
  start: [payload: { index: number }]
  end: [payload: { oldIndex: number; newIndex: number }]
  change: [payload: { moved: any; from: number; to: number }]
  add: [payload: { element: any; newIndex: number }]
}>()

// ─── DOM refs ───────────────────────────────────────────────

const containerRef = ref<HTMLElement | null>(null)

// ─── Drag state ─────────────────────────────────────────────

const isDragging = ref(false)
const dragIndex = ref(-1) // 被拖拽项的原始下标
const dropIndex = ref(-1) // 当前落点下标（0 ~ length，length 表示末尾）
const ghostStyle = reactive({
  top: '0px',
  left: '0px',
  width: '0px',
  height: '0px'
})

// 每项的 transform 偏移（用于让位动画）
const itemTransforms = reactive<Record<number, string>>({})

// ─── 拖拽过程中暂存的数据 ─────────────────────────────────

let dragData = {
  itemEl: null as HTMLElement | null,
  cloneEl: null as HTMLElement | null,
  startX: 0,
  startY: 0,
  offsetX: 0, // 鼠标在元素内的 X 偏移
  offsetY: 0, // 鼠标在元素内的 Y 偏移
  itemRect: null as DOMRect | null,
  fromIndex: -1
}

// RAF 节流：把多次 pointermove 压缩到每帧一次
let rafId = 0
let pendingX = 0
let pendingY = 0

// ─── Key 解析 ───────────────────────────────────────────────

function getItemKey(item: any, index: number): string | number {
  if (props.itemKey) {
    return typeof props.itemKey === 'function' ? props.itemKey(item, index) : item[props.itemKey]
  }
  return index
}

// ─── 拖拽核心 ───────────────────────────────────────────────

function onPointerDown(e: PointerEvent) {
  // 如果有 handle 选择器，检查点击目标是否在 handle 内
  if (props.handle) {
    const target = e.target as HTMLElement
    const handleEl = target.closest(props.handle)
    if (!handleEl) return
    // 从 handle 往上找所属的 sortable item
    const itemEl = handleEl.closest('[data-ar-sortable-index]') as HTMLElement | null
    if (!itemEl) return
    const index = parseInt(itemEl.dataset.arSortableIndex || '-1')
    if (index < 0) return
    startDrag(e, index)
    return
  }

  // 无 handle：整个 item 区域都可拖
  const itemEl = (e.target as HTMLElement).closest('[data-ar-sortable-index]') as HTMLElement | null
  if (!itemEl) return
  const index = parseInt(itemEl.dataset.arSortableIndex || '-1')
  if (index < 0) return
  startDrag(e, index)
}

function startDrag(e: PointerEvent, index: number) {
  const container = containerRef.value
  if (!container || props.modelValue.length === 0) return

  const items = getItemElements()
  const itemEl = items[index]
  if (!itemEl) return

  const rect = itemEl.getBoundingClientRect()

  // 记录拖拽起始状态
  dragData.itemRect = rect
  dragData.fromIndex = index
  dragData.startX = e.clientX
  dragData.startY = e.clientY
  dragData.offsetX = e.clientX - rect.left
  dragData.offsetY = e.clientY - rect.top

  // 创建克隆体
  const clone = itemEl.cloneNode(true) as HTMLElement
  clone.classList.add('ar-sortable__clone')
  // 去掉克隆体继承的多余属性，避免干扰
  clone.removeAttribute('data-ar-sortable-index')
  clone.style.transition = 'none'
  // 脱离父容器后 width 会丢失，显式继承
  clone.style.width = `${rect.width}px`
  // 去掉 margin（卡片之间的间距），避免克隆体底部多出空白
  clone.style.margin = '0'
  // 克隆内部的 paragraph-card 也去掉 margin（否则 margin 造成克隆体比原卡多一截）
  const innerCard = clone.querySelector('.paragraph-card') as HTMLElement | null
  if (innerCard) {
    innerCard.style.margin = '0'
  }
  // 防止克隆体里的手柄/按钮响应事件
  clone.style.setProperty('pointer-events', 'none')
  document.body.appendChild(clone)
  dragData.cloneEl = clone

  // 隐藏原始元素
  itemEl.style.opacity = '0'
  dragData.itemEl = itemEl

  // 设置克隆体位 + 样式
  updateClonePosition(e.clientX, e.clientY)

  // 更新 UI 状态
  isDragging.value = true
  dragIndex.value = index
  dropIndex.value = index

  // ghost 初始位置在当前项
  updateGhostPosition(index)

  // 全局事件监听
  document.addEventListener('pointermove', onPointerMove)
  document.addEventListener('pointerup', onPointerUp)
  document.addEventListener('pointercancel', onPointerUp)

  // 防止文本选中
  document.body.style.userSelect = 'none'

  emit('start', { index })
}

/** 获取当前所有 item DOM 元素 */
function getItemElements(): HTMLElement[] {
  const container = containerRef.value
  if (!container) return []
  return Array.from(container.children).filter(
    (el) => el instanceof HTMLElement && el.dataset.arSortableIndex !== undefined
  ) as HTMLElement[]
}

function onPointerMove(e: PointerEvent) {
  e.preventDefault()
  // RAF 节流：只保留最新坐标，每帧统一处理一次
  pendingX = e.clientX
  pendingY = e.clientY
  if (!rafId) {
    rafId = requestAnimationFrame(flushDragMove)
  }
}

function flushDragMove() {
  rafId = 0
  updateClonePosition(pendingX, pendingY)

  // 计算当前落点下标，只更新 ghost 提示线位置
  const targetIndex = calcDropIndex(pendingX, pendingY)
  if (targetIndex !== dropIndex.value) {
    dropIndex.value = targetIndex
    updateGhostPosition(targetIndex)
    updateItemTransforms()
  }
}

function onPointerUp() {
  // 确保最后一次位置更新已执行（RAF 可能还没触发）
  if (rafId) {
    cancelAnimationFrame(rafId)
    rafId = 0
  }
  flushDragMove()
  finishDrag()
  cleanupDrag()
}

/** 完成拖拽：调整数组顺序 */
function finishDrag() {
  const from = dragData.fromIndex
  const to = dropIndex.value
  if (from < 0 || to < 0) return

  // 移除克隆体
  if (dragData.cloneEl) {
    dragData.cloneEl.remove()
    dragData.cloneEl = null
  }

  // 恢复原始元素可见
  if (dragData.itemEl) {
    dragData.itemEl.style.opacity = ''
    dragData.itemEl = null
  }

  if (from !== to && from >= 0 && to >= 0) {
    const arr = [...props.modelValue]
    const [moved] = arr.splice(from, 1)
    const adjustedTo = to > from ? to - 1 : to
    arr.splice(adjustedTo, 0, moved)
    emit('update:modelValue', arr)
    emit('change', { moved, from, to: adjustedTo })
  }

  dragData.fromIndex = -1
  emit('end', { oldIndex: from, newIndex: to })
}

/** 清理拖拽状态 */
function cleanupDrag() {
  isDragging.value = false
  dragIndex.value = -1
  dropIndex.value = -1

  // 清除让位动画
  for (const key in itemTransforms) {
    delete itemTransforms[key]
  }

  if (rafId) {
    cancelAnimationFrame(rafId)
    rafId = 0
  }

  document.removeEventListener('pointermove', onPointerMove)
  document.removeEventListener('pointerup', onPointerUp)
  document.removeEventListener('pointercancel', onPointerUp)
  document.body.style.userSelect = ''
}

// ─── 克隆体定位 ────────────────────────────────────────────

function updateClonePosition(cx: number, cy: number) {
  const rect = dragData.itemRect
  const clone = dragData.cloneEl
  if (!rect || !clone) return

  const axis = props.axis
  let left: number, top: number

  if (axis === 'y') {
    left = rect.left
    top = cy - dragData.offsetY
  } else if (axis === 'x') {
    left = cx - dragData.offsetX
    top = rect.top
  } else {
    left = cx - dragData.offsetX
    top = cy - dragData.offsetY
  }

  clone.style.left = `${left}px`
  clone.style.top = `${top}px`
}

// ─── 落点计算 ──────────────────────────────────────────────

function calcDropIndex(cx: number, cy: number): number {
  const items = getItemElements()
  if (items.length === 0) return 0
  const from = dragData.fromIndex

  if (props.axis === 'y') {
    // 计算鼠标 Y 坐标相对于每项的位置
    for (let i = 0; i < items.length; i++) {
      if (i === from) continue // 跳过自身
      const rect = items[i].getBoundingClientRect()
      const midY = rect.top + rect.height / 2
      if (cy < midY) return i
    }
    // 如果鼠标在所有项的下方，插入到末尾
    // 但如果 from 是最后一项，最后一项的位置需要特殊处理
    return items.length
  }

  if (props.axis === 'x') {
    for (let i = 0; i < items.length; i++) {
      if (i === from) continue
      const rect = items[i].getBoundingClientRect()
      const midX = rect.left + rect.width / 2
      if (cx < midX) return i
    }
    return items.length
  }

  // XY 轴：先从 Y 找，再从 X 找
  for (let i = 0; i < items.length; i++) {
    if (i === from) continue
    const rect = items[i].getBoundingClientRect()
    const midY = rect.top + rect.height / 2
    if (cy < midY) return i
  }
  return items.length
}

// ─── 常量 ──────────────────────────────────────────────────

/** 卡片之间的默认间隙（当无法从 CSS 读取时回退） */
const DEFAULT_CARD_GAP = 16

// ─── Ghost 定位 ────────────────────────────────────────────

/** 获取卡片之间的间隙（取 marginBottom 或 marginTop 中的非零值） */
function getItemGap(): number {
  const items = getItemElements()
  if (items.length === 0) return DEFAULT_CARD_GAP
  const card = items[0].querySelector('.paragraph-card') as HTMLElement | null
  if (card) {
    const cs = getComputedStyle(card)
    const mb = parseFloat(cs.marginBottom)
    if (!isNaN(mb) && mb > 0) return mb
    const mt = parseFloat(cs.marginTop)
    if (!isNaN(mt) && mt > 0) return mt
  }
  return DEFAULT_CARD_GAP
}

/** 计算两个相邻卡片之间的纵轴居中位置 */
function updateGhostPosition(targetIndex: number) {
  const items = getItemElements()
  const container = containerRef.value
  if (items.length === 0 || !container) return

  const containerRect = container.getBoundingClientRect()
  const gap = getItemGap()

  if (targetIndex >= items.length) {
    const lastRect = items[items.length - 1].getBoundingClientRect()
    // 放到卡片底边 + 半个间隙的位置，落在间隙中间而不是卡片内部
    ghostStyle.top = `${lastRect.bottom - containerRect.top + gap / 2}px`
  } else if (targetIndex <= 0) {
    const firstRect = items[0].getBoundingClientRect()
    // 放到卡片顶边 - 半个间隙的位置
    ghostStyle.top = `${firstRect.top - containerRect.top - gap / 2}px`
  } else {
    const prevRect = items[targetIndex - 1].getBoundingClientRect()
    const currRect = items[targetIndex].getBoundingClientRect()
    ghostStyle.top = `${(prevRect.bottom + currRect.top) / 2 - containerRect.top}px`
  }

  ghostStyle.left = '0px'
  ghostStyle.width = `${containerRect.width}px`
  ghostStyle.height = '2px'
}

// ─── 让位动画 ──────────────────────────────────────────────

/** 获取一个 item 的外高度（含到下一项的间隙） */
function getItemOuterHeight(item: HTMLElement): number {
  return item.getBoundingClientRect().height
}

/** 根据 ghost 位置更新各 item 的 transform（让位弹开效果） */
function updateItemTransforms() {
  // 清除旧变换
  for (const key in itemTransforms) {
    delete itemTransforms[key]
  }

  const items = getItemElements()
  const from = dragData.fromIndex
  const to = dropIndex.value
  if (from < 0 || to < 0 || items.length === 0 || from === to) return

  if (to > from) {
    // 向下拖：from+1 ~ to 之间的项逐个上移，在 to 位置腾出空位
    for (let i = from + 1; i <= to && i < items.length; i++) {
      const h = getItemOuterHeight(items[i])
      if (h > 0) itemTransforms[i] = `translateY(-${h}px)`
    }
  } else {
    // 向上拖：to ~ from-1 之间的项逐个下移，在 to 位置腾出空位
    for (let i = to; i < from; i++) {
      const h = getItemOuterHeight(items[i])
      if (h > 0) itemTransforms[i] = `translateY(${h}px)`
    }
  }
}

// ─── 外部元素拖入（HTML5 Drag API） ─────────────────────

let externalDropIndex = -1

function calcExternalDropIndex(cx: number, cy: number): number {
  const items = getItemElements()
  if (items.length === 0) return 0
  for (let i = 0; i < items.length; i++) {
    const rect = items[i].getBoundingClientRect()
    if (props.axis === 'y') {
      if (cy < rect.top + rect.height / 2) return i
    } else if (props.axis === 'x') {
      if (cx < rect.left + rect.width / 2) return i
    } else {
      if (cy < rect.top + rect.height / 2) return i
    }
  }
  return items.length
}

function onDragOver(e: DragEvent) {
  e.preventDefault()
  if (e.dataTransfer) {
    e.dataTransfer.dropEffect = 'copy'
  }
  externalDropIndex = calcExternalDropIndex(e.clientX, e.clientY)
}

function onDrop(e: DragEvent) {
  e.preventDefault()
  const raw = e.dataTransfer?.getData('Text')
  if (!raw) return
  const index = externalDropIndex >= 0 ? externalDropIndex : props.modelValue.length
  emit('add', { element: raw, newIndex: index })
  externalDropIndex = -1
}
</script>

<template>
  <div
    ref="containerRef"
    class="ar-sortable"
    :class="[`ar-sortable--${axis}`, { 'ar-sortable--dragging': isDragging }]"
    @dragover="onDragOver"
    @drop="onDrop"
    @pointerdown="onPointerDown"
  >
    <div
      v-for="(item, index) in modelValue"
      :key="getItemKey(item, index)"
      class="ar-sortable__item"
      :data-ar-sortable-index="index"
      :style="itemTransforms[index] ? { transform: itemTransforms[index] } : undefined"
    >
      <slot name="item" :element="item" :index="index" />
    </div>

    <!-- Ghost 占位 — 拖拽中显示在落点位置 -->
    <div v-if="isDragging" class="ar-sortable__ghost" :style="ghostStyle">
      <slot name="ghost" :index="dropIndex">
        <div class="ar-sortable__ghost-inner" :class="`ar-sortable__ghost-inner--${ghost}`" />
      </slot>
    </div>
  </div>
</template>

<style scoped>
.ar-sortable {
  position: relative;
  min-width: 0;
}

.ar-sortable__item {
  position: relative;
  z-index: 1;
  transition: transform 150ms ease;
}

/* 拖拽中禁用 transition（避免与 getBoundingClientRect 形成反馈环路），
   同时防止意外的鼠标交互影响 item 内部 */
.ar-sortable--dragging .ar-sortable__item {
  transition: none !important;
  pointer-events: none;
}

/* ─── 克隆体 ─── */

.ar-sortable__clone {
  position: fixed;
  z-index: 9999;
  opacity: 1;
  pointer-events: none;
  box-shadow: var(--card-shadow-elevated);
  border-radius: var(--radius-md);
  will-change: top, left;
}

/* ─── Ghost ─── */

.ar-sortable__ghost {
  position: absolute;
  z-index: 2;
  pointer-events: none;
}

/* 预设：line — 水平虚线 */
.ar-sortable__ghost-inner--line {
  border-top: 2px dashed var(--primary-color);
  height: 0;
  margin: 0;
}

/* 预设：box — 虚线框 */
.ar-sortable__ghost-inner--box {
  border: 2px dashed var(--primary-color);
  border-radius: var(--radius-md);
  background: rgba(128, 128, 128, 0.04);
  height: 100%;
  box-sizing: border-box;
}

/* 预设：none — 透明 */
.ar-sortable__ghost-inner--none {
  height: 0;
}
</style>
