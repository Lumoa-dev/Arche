<script setup lang="ts">
/**
 * WatchHistoryStack — 继续观看 · 平铺横滚
 *
 * 卡片平铺排列，鼠标滚轮/拖拽滚动，两端限位卡片提示上限并支持跳转。
 */
import { computed, onBeforeUnmount, ref } from 'vue'
import type { BlogPost } from '@/components/logic/api'
import PostCard from './PostCard.vue'

export interface WatchHistoryItem {
  post: BlogPost
  progress?: number
  lastReadAt?: string
}

const MAX_ITEMS = 50

const props = withDefaults(
  defineProps<{
    items: WatchHistoryItem[]
  }>(),
  {}
)

const emit = defineEmits<{
  open: [item: WatchHistoryItem]
  viewAll: []
}>()

const dedupedItems = computed(() => {
  const seen = new Set<string>()
  return props.items
    .filter((item) => {
      // 去重 + 过滤已读完（progress >= 100）
      if (seen.has(item.post.id)) return false
      seen.add(item.post.id)
      if (item.progress != null && item.progress >= 100) return false
      return true
    })
    .slice(0, MAX_ITEMS)
})

// ── 滚动容器 ──
const viewportRef = ref<HTMLElement | null>(null)

// ── 鼠标滚轮 → 水平平滑滚动 ──
function onWheel(e: WheelEvent) {
  const el = viewportRef.value
  if (!el) return
  e.preventDefault()
  el.scrollBy({ left: e.deltaY, behavior: 'smooth' })
}

// ── 鼠标拖拽 → 水平滚动 ──
let dragStartX = 0
let dragStartScroll = 0
let isDragging = false

function startDrag(e: MouseEvent) {
  // 忽略拖动限位卡和卡片内的点击
  const target = e.target as HTMLElement
  if (target.closest('.boundary-card') || target.closest('.post-card')) return

  isDragging = true
  dragStartX = e.clientX
  dragStartScroll = viewportRef.value?.scrollLeft ?? 0
  window.addEventListener('mousemove', onDragMove)
  window.addEventListener('mouseup', stopDrag)
}

function onDragMove(e: MouseEvent) {
  if (!isDragging || !viewportRef.value) return
  const delta = e.clientX - dragStartX
  viewportRef.value.scrollLeft = dragStartScroll - delta
}

function stopDrag() {
  isDragging = false
  window.removeEventListener('mousemove', onDragMove)
  window.removeEventListener('mouseup', stopDrag)
}

onBeforeUnmount(() => {
  stopDrag()
})

// ── 估算阅读时长 ──
function estimateDuration(post: BlogPost): string {
  const text = post.introduction?.abstract || post.title || ''
  const len = text.replace(/<[^>]+>/g, '').length
  return `${Math.max(1, Math.ceil(len / 300))} 分钟`
}
</script>

<template>
  <section class="watch-history">
    <div class="section-head">
      <div class="section-title-group">
        <span class="section-icon">&#9654;</span>
        <h3 class="section-title">继续观看</h3>
      </div>
      <span class="section-hint">{{ dedupedItems.length }} 条待读</span>
    </div>

    <div ref="viewportRef" class="scroll-viewport" @wheel="onWheel" @mousedown="startDrag">
      <div class="scroll-track">
        <!-- 左端限位卡 -->
        <article class="boundary-card" @click="emit('viewAll')">
          <div class="boundary-body">
            <svg class="boundary-arrow" width="28" height="28" viewBox="0 0 24 24" fill="none">
              <path
                d="M19 12H5M5 12L12 19M5 12L12 5"
                stroke="currentColor"
                stroke-width="1.8"
                stroke-linecap="round"
                stroke-linejoin="round"
              />
            </svg>
            <span class="boundary-label">浏览全部</span>
            <span class="boundary-hint">共 {{ dedupedItems.length }} 条记录</span>
          </div>
        </article>

        <!-- 实际卡片 -->
        <article
          v-for="item in dedupedItems"
          :key="item.post.id"
          class="scroll-card"
          @click="emit('open', item)"
        >
          <PostCard
            mode="cover"
            :post="item.post"
            :meta-progress="item.progress ?? 0"
            :meta-duration="estimateDuration(item.post)"
          />
        </article>

        <!-- 右端限位卡 -->
        <article class="boundary-card" @click="emit('viewAll')">
          <div class="boundary-body">
            <span class="boundary-label">浏览全部</span>
            <span class="boundary-hint">共 {{ dedupedItems.length }} 条记录</span>
            <svg class="boundary-arrow" width="28" height="28" viewBox="0 0 24 24" fill="none">
              <path
                d="M5 12H19M19 12L12 5M19 12L12 19"
                stroke="currentColor"
                stroke-width="1.8"
                stroke-linecap="round"
                stroke-linejoin="round"
              />
            </svg>
          </div>
        </article>
      </div>
    </div>
  </section>
</template>

<style scoped>
.watch-history {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
  user-select: none;
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: var(--spacing-md);
}

.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 2px;
}

.section-title-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.section-icon {
  font-size: 10px;
  color: var(--primary-color);
  opacity: 0.7;
}

.section-title {
  margin: 0;
  font-size: 18px;
  font-weight: var(--font-weight-semibold);
  color: var(--text-primary);
  letter-spacing: -0.02em;
}

.section-hint {
  font-size: 12px;
  color: var(--text-tertiary);
}

.scroll-viewport {
  overflow-x: auto;
  overflow-y: hidden;
  scrollbar-width: none;
  scroll-behavior: smooth;
  cursor: grab;
}

.scroll-viewport:active {
  cursor: grabbing;
}

.scroll-viewport::-webkit-scrollbar {
  display: none;
}

.scroll-track {
  display: flex;
  gap: 14px;
  padding: 4px 0;
  pointer-events: none;
}

.scroll-track > * {
  pointer-events: auto;
}

.scroll-card {
  flex: 0 0 270px;
  height: 170px;
  border-radius: var(--radius-lg);
  overflow: hidden;
  cursor: pointer;
  box-shadow:
    0 2px 8px rgba(26, 24, 23, 0.08),
    0 1px 3px rgba(26, 24, 23, 0.04);
  transition: box-shadow 0.25s ease;
}

.scroll-card:hover {
  box-shadow:
    0 0 0 2px var(--primary-color),
    0 4px 16px -6px rgba(26, 24, 23, 0.15),
    0 1px 4px -2px rgba(26, 24, 23, 0.08);
}

/* ═══════════════════════════════════════
   限位卡片
   ═══════════════════════════════════════ */
.boundary-card {
  flex: 0 0 160px;
  height: 170px;
  border-radius: var(--radius-lg);
  border: 1.5px dashed var(--border-color);
  cursor: pointer;
  transition:
    border-color 0.25s ease,
    background 0.25s ease;
  display: flex;
  align-items: center;
  justify-content: center;
}

.boundary-card:hover {
  border-color: var(--primary-color);
  background: var(--primary-light-color);
}

.boundary-body {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 10px;
  text-align: center;
}

.boundary-arrow {
  color: var(--text-tertiary);
  transition: color 0.25s ease;
}

.boundary-card:hover .boundary-arrow {
  color: var(--primary-color);
}

.boundary-label {
  font-size: 13px;
  font-weight: var(--font-weight-semibold);
  color: var(--text-secondary);
  transition: color 0.25s ease;
}

.boundary-card:hover .boundary-label {
  color: var(--primary-color);
}

.boundary-hint {
  font-size: 11px;
  color: var(--text-tertiary);
}

:global(.dark) .scroll-card:hover {
  box-shadow:
    0 0 0 2px var(--primary-color),
    0 4px 16px -6px rgba(0, 0, 0, 0.4),
    0 1px 4px -2px rgba(0, 0, 0, 0.2);
}

:global(.dark) .boundary-card {
  border-color: rgba(230, 225, 218, 0.15);
}

:global(.dark) .boundary-card:hover {
  border-color: var(--primary-color);
  background: rgba(212, 74, 58, 0.1);
}
</style>
