<script setup lang="ts">
/**
 * ArSideNav — 侧边导航栏布局原语
 *
 * 纯布局组件，只关心结构和样式。
 * 支持折叠、分组、条目拖拽排序、左右布局。
 * 所有内容通过 props 驱动，事件通过 emit 上抛。
 */
import { ref } from 'vue'
import type { Component } from 'vue'

export interface ArNavItem {
  id: string
  label: string
  icon?: Component
  badge?: string | number
  disabled?: boolean
}

export interface ArNavGroup {
  id: string
  title?: string
  items: ArNavItem[]
}

const props = withDefaults(
  defineProps<{
    /** 布局模式 */
    mode: 'thin' | 'normal' | 'grouped'
    /** 导航条目（thin/normal 模式） */
    items?: ArNavItem[]
    /** 导航分组（grouped 模式） */
    groups?: ArNavGroup[]
    /** 是否折叠 */
    collapsed?: boolean
    /** 当前活跃条目 id */
    activeId?: string
    /** 是否支持拖拽排序 */
    draggable?: boolean
    /** 侧边栏位置 */
    position?: 'left' | 'right'
  }>(),
  {
    items: () => [],
    groups: () => [],
    collapsed: false,
    activeId: '',
    draggable: false,
    position: 'left'
  }
)

const emit = defineEmits<{
  /** 选中条目 */
  select: [id: string]
  /** 切换折叠 */
  'update:collapsed': [v: boolean]
  /** 拖拽排序后触发 */
  reorder: [payload: { groupId?: string; items: string[] }]
}>()

// ── 拖拽状态 ──
const dragIndex = ref(-1)
const dragGroupId = ref('')

function onDragStart(e: DragEvent, index: number, groupId?: string) {
  if (!props.draggable) return
  dragIndex.value = index
  dragGroupId.value = groupId ?? ''
  if (e.dataTransfer) {
    e.dataTransfer.effectAllowed = 'move'
  }
}

function onDragOver(e: DragEvent) {
  if (!props.draggable) return
  e.preventDefault()
  if (e.dataTransfer) {
    e.dataTransfer.dropEffect = 'move'
  }
}

function onDrop(e: DragEvent, targetIndex: number, groupId?: string) {
  if (!props.draggable) return
  e.preventDefault()
  const from = dragIndex.value
  const to = targetIndex
  if (from === to || from < 0) return

  const gId = dragGroupId.value || groupId || ''
  const sourceItems = gId ? (props.groups.find((g) => g.id === gId)?.items ?? []) : props.items
  const ids = sourceItems.map((item) => item.id)
  const [moved] = ids.splice(from, 1)
  if (moved) {
    ids.splice(to, 0, moved)
    emit('reorder', { groupId: gId || undefined, items: ids })
  }

  dragIndex.value = -1
  dragGroupId.value = ''
}

function onDragEnd() {
  dragIndex.value = -1
  dragGroupId.value = ''
}
</script>

<template>
  <aside
    class="ar-side-nav"
    :class="[
      `ar-side-nav--${mode}`,
      `ar-side-nav--${position}`,
      {
        'is-collapsed': collapsed,
        'is-draggable': draggable
      }
    ]"
  >
    <!-- 顶部插槽 -->
    <div v-if="$slots.header" class="ar-side-nav__header">
      <slot name="header" />
    </div>

    <nav class="ar-side-nav__body">
      <!-- ── Thin 模式 ── -->
      <template v-if="mode === 'thin'">
        <button
          v-for="item in items"
          :key="item.id"
          class="ar-side-nav__item"
          :class="{ 'is-active': activeId === item.id, 'is-disabled': item.disabled }"
          :disabled="item.disabled"
          @click="!item.disabled && emit('select', item.id)"
        >
          <slot name="item" :item="item">
            <span class="ar-side-nav__item-label">{{ item.label }}</span>
          </slot>
        </button>
      </template>

      <!-- ── Normal 模式 ── -->
      <template v-else-if="mode === 'normal'">
        <button
          v-for="(item, i) in items"
          :key="item.id"
          class="ar-side-nav__item"
          :class="{ 'is-active': activeId === item.id, 'is-disabled': item.disabled }"
          :disabled="item.disabled"
          draggable="false"
          @dragstart="onDragStart($event, i)"
          @dragover="onDragOver($event)"
          @drop="onDrop($event, i)"
          @dragend="onDragEnd"
          @click="!item.disabled && emit('select', item.id)"
        >
          <slot name="item" :item="item">
            <component :is="item.icon" v-if="item.icon" class="ar-side-nav__item-icon" />
            <span v-if="!collapsed" class="ar-side-nav__item-label">{{ item.label }}</span>
            <span v-if="!collapsed && item.badge" class="ar-side-nav__item-badge">{{
              item.badge
            }}</span>
          </slot>
        </button>
      </template>

      <!-- ── Grouped 模式 ── -->
      <template v-else-if="mode === 'grouped'">
        <div v-for="group in groups" :key="group.id" class="ar-side-nav__group">
          <slot name="group-header" :group="group">
            <span v-if="!collapsed && group.title" class="ar-side-nav__group-title">{{
              group.title
            }}</span>
          </slot>
          <button
            v-for="(item, i) in group.items"
            :key="item.id"
            class="ar-side-nav__item"
            :class="{ 'is-active': activeId === item.id, 'is-disabled': item.disabled }"
            :disabled="item.disabled"
            @dragstart="onDragStart($event, i, group.id)"
            @dragover="onDragOver($event)"
            @drop="onDrop($event, i, group.id)"
            @dragend="onDragEnd"
            @click="!item.disabled && emit('select', item.id)"
          >
            <slot name="item" :item="item">
              <component :is="item.icon" v-if="item.icon" class="ar-side-nav__item-icon" />
              <span v-if="!collapsed" class="ar-side-nav__item-label">{{ item.label }}</span>
              <span v-if="!collapsed && item.badge" class="ar-side-nav__item-badge">{{
                item.badge
              }}</span>
            </slot>
          </button>
        </div>
      </template>
    </nav>

    <!-- 底部插槽 -->
    <div v-if="$slots.footer" class="ar-side-nav__footer">
      <slot name="footer" />
    </div>
  </aside>
</template>

<style scoped>
.ar-side-nav {
  position: fixed;
  top: 56px;
  bottom: 0;
  overflow-y: auto;
  overscroll-behavior: contain;
  background: var(--surface-solid);
  border-color: var(--border-color);
  z-index: 90;
  display: flex;
  flex-direction: column;
  transition:
    width var(--transition-slow) var(--ease-out-spring),
    transform var(--transition-slow) var(--ease-out-spring);
}

.ar-side-nav--left {
  left: 0;
  border-right-width: 1px;
  border-right-style: solid;
}

.ar-side-nav--right {
  right: 0;
  border-left-width: 1px;
  border-left-style: solid;
}

/* ── 各模式宽度 ── */
.ar-side-nav--thin {
  width: 180px;
}

.ar-side-nav--normal,
.ar-side-nav--grouped {
  width: 240px;
}

.ar-side-nav--normal.is-collapsed,
.ar-side-nav--grouped.is-collapsed {
  width: 64px;
}

/* ── Header / Footer ── */
.ar-side-nav__header,
.ar-side-nav__footer {
  flex-shrink: 0;
}

/* ── Body ── */
.ar-side-nav__body {
  flex: 1;
  overflow-y: auto;
  padding: var(--spacing-sm) 0;
}

.ar-side-nav--thin .ar-side-nav__body {
  padding: var(--spacing-md);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

/* ── Group ── */
.ar-side-nav__group + .ar-side-nav__group {
  margin-top: var(--spacing-md);
}

.ar-side-nav__group-title {
  display: block;
  padding: var(--spacing-sm) var(--spacing-lg);
  font-size: 11px;
  color: var(--text-tertiary);
  font-weight: var(--font-weight-semibold);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* ── Item ── */
.ar-side-nav__item {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 10px 16px;
  margin: 0 var(--spacing-sm);
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  text-decoration: none;
  transition: all var(--transition-fast);
  font-size: 14px;
  font-weight: var(--font-weight-medium);
  border: none;
  background: none;
  cursor: pointer;
  font-family: inherit;
  text-align: left;
  /* 限制宽度确保 margin 有效 */
  width: calc(100% - var(--spacing-sm) * 2);
}

.ar-side-nav--thin .ar-side-nav__item {
  display: block;
  padding: 8px 12px;
  margin: 0;
  width: 100%;
}

/* 拖拽时高亮 */
.is-draggable .ar-side-nav__item:not(.is-disabled) {
  cursor: grab;
}

.is-draggable .ar-side-nav__item:not(.is-disabled):active {
  cursor: grabbing;
}

.ar-side-nav__item:hover {
  background: var(--primary-light-color);
  color: var(--primary-color);
}

.ar-side-nav__item.is-active {
  background: var(--primary-color);
  color: var(--text-on-primary, #fff);
}

.ar-side-nav--thin .ar-side-nav__item.is-active {
  background: var(--primary-light-color);
  color: var(--primary-color);
  font-weight: var(--font-weight-semibold);
}

.ar-side-nav__item.is-disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.ar-side-nav__item-icon {
  font-size: 20px;
  flex-shrink: 0;
}

.ar-side-nav__item-label {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ar-side-nav__item-badge {
  flex-shrink: 0;
  min-width: 18px;
  height: 18px;
  padding: 0 5px;
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-semibold);
  border-radius: var(--radius-full);
  background: var(--primary-light-color);
  color: var(--primary-color);
  display: flex;
  align-items: center;
  justify-content: center;
}

/* ── Thin 模式下 badge ── */
.ar-side-nav--thin .ar-side-nav__item-badge {
  display: none;
}

/* ── 折叠时隐藏文字 ── */
.is-collapsed .ar-side-nav__item-label,
.is-collapsed .ar-side-nav__group-title,
.is-collapsed .ar-side-nav__item-badge {
  display: none;
}

.is-collapsed .ar-side-nav__item {
  justify-content: center;
  padding: 10px 0;
  margin: 0 auto;
  width: 44px;
}

.is-collapsed .ar-side-nav__item-icon {
  margin: 0;
}

/* ── 滚动条 ── */
.ar-side-nav__body::-webkit-scrollbar,
.ar-side-nav::-webkit-scrollbar {
  width: 4px;
}

.ar-side-nav__body::-webkit-scrollbar-track,
.ar-side-nav::-webkit-scrollbar-track {
  background: transparent;
}

.ar-side-nav__body::-webkit-scrollbar-thumb,
.ar-side-nav::-webkit-scrollbar-thumb {
  background: var(--primary-light-color);
  border-radius: 2px;
}

.ar-side-nav__body::-webkit-scrollbar-thumb:hover,
.ar-side-nav::-webkit-scrollbar-thumb:hover {
  background: color-mix(in srgb, var(--primary-color) 34%, transparent);
}
</style>
