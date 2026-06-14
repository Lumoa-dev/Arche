<script setup lang="ts">
/**
 * ArCarousel3D — 通用 3D 卡片堆叠轮播组件。
 *
 * 核心视觉：中间一张主卡，左右卡片一层叠一层无限延伸，
 * 遵循近大远小透视规律。参照 iOS 后台卡片堆叠效果。
 *
 * @slot card — 卡片内容
 *   slot props: { item, index, isMain, showOverlay }
 *
 * 未来计划：
 * - 主题体系：预设暗色/亮色/多彩主题，覆写阴影/渐变/遮罩
 * - API 驱动：传入 fetch 函数，自动分页加载 + 无限滚动
 * - 动效扩展：裸眼 3D（视差追踪）、WebGL 粒子背景
 * - 手势支持：触摸拖拽 + 惯性滑动
 *
 * @example
 * ```vue
 * <ArCarousel3D :items="products" :interval="5000">
 *   <template #card="{ item, isMain }">
 *     <img :src="item.image" />
 *     <div class="price">{{ item.price }}</div>
 *   </template>
 * </ArCarousel3D>
 * ```
 */
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useSpring } from '@/lib/utils/spring'

// ── Props ──
const props = withDefaults(
  defineProps<{
    items: any[]
    interval?: number
    /** 卡片宽度（px），影响堆叠间距和遮罩范围 */
    cardWidth?: number
  }>(),
  { interval: 12000, cardWidth: 280 }
)

// ── Slots ──
defineSlots<{
  // eslint-disable-next-line no-unused-vars
  card(_props: { item: any; index: number; isMain: boolean; showOverlay: boolean }): any
}>()

// ── 透视常量 ──
const CARD_W = computed(() => props.cardWidth)
const POS_FACTOR = 0.47
const SCALE_FACTOR = 0.18
const MAX_SPREAD = 560
const COPIES = 5
const MID = Math.floor(COPIES / 2)

const displayItems = computed(() => {
  if (props.items.length === 0) return []
  const result: any[] = []
  for (let c = 0; c < COPIES; c++) result.push(...props.items)
  return result
})
const N = computed(() => props.items.length)

// ── 弹簧驱动索引 ──
const targetIdx = ref(MID * N.value)
const { value: animatedIdx, jump } = useSpring(targetIdx, {
  stiffness: 160,
  damping: 22,
  precision: 0.3
})

// ── 当前指示点 ──
const activeDot = computed(() => {
  return ((Math.round(animatedIdx.value) % N.value) + N.value) % N.value
})

// ── 场景尺寸 ──
const sceneRef = ref<HTMLElement | null>(null)
const sceneW = ref(800)
const sceneH = computed(() => Math.max(240, (CARD_W.value * 3) / 4 + 40))

// ── 卡片堆叠变换 ──
const cardStates = computed(() => {
  const cw = CARD_W.value
  return displayItems.value.map((_, i) => {
    const n = i - animatedIdx.value
    const abs = Math.abs(n)
    const sign = Math.sign(n) || 1

    const t = 1 - 1 / (1 + abs * POS_FACTOR)
    const xOffset = sign * t * MAX_SPREAD
    const scale = 1 / (1 + abs * SCALE_FACTOR)
    const opacity = 1 / (1 + Math.pow(Math.max(0, abs - 0.5), 2) * 0.5)
    const blurAmt = abs <= 0.5 ? 0 : Math.min(4, (abs - 0.5) * 1.5)
    const transformX = xOffset - cw / 2
    const si = Math.max(0, 1 - abs * 0.25)
    const shadow = [
      `0 ${(1.5 * scale).toFixed(1)}px ${(4 * scale).toFixed(1)}px rgba(26,24,23,${(
        0.05 * si
      ).toFixed(3)})`,
      `0 ${(6 * scale).toFixed(1)}px ${(18 * scale).toFixed(1)}px rgba(26,24,23,${(
        0.08 * si
      ).toFixed(3)})`,
      `0 ${(18 * scale).toFixed(1)}px ${(50 * scale).toFixed(1)}px rgba(26,24,23,${(
        0.06 * si
      ).toFixed(3)})`
    ].join(', ')

    return {
      transform: `translateX(${transformX}px) translateY(-50%) scale(${scale})`,
      filter: blurAmt > 0 ? `blur(${blurAmt}px)` : 'none',
      boxShadow: shadow,
      opacity,
      zIndex: Math.max(0, 10 - Math.round(abs)),
      pe: (abs < 1.5 ? 'auto' : 'none') as 'auto' | 'none'
    }
  })
})

function getStyle(i: number) {
  return cardStates.value[i] ?? {}
}

function cardAtMain(i: number): boolean {
  return i === Math.round(animatedIdx.value)
}

function showOverlay(i: number): boolean {
  return Math.abs(i - Math.round(animatedIdx.value)) <= 1
}

// ── 交互 ──
const emit = defineEmits<{
  select: [item: any]
}>()

function handleCardClick(item: any, i: number) {
  const diff = i - Math.round(animatedIdx.value)
  if (diff === 0) {
    emit('select', item)
  } else if (Math.abs(diff) === 1) {
    targetIdx.value = i
    resetTimer()
  }
}

function goNext() {
  if (N.value <= 1) return
  targetIdx.value = targetIdx.value + 1
  resetTimer()
}

function goPrev() {
  if (N.value <= 1) return
  targetIdx.value = targetIdx.value - 1
  resetTimer()
}

function goTo(idx: number) {
  const current = Math.round(animatedIdx.value)
  const currentCopy = Math.floor(current / N.value)
  targetIdx.value = currentCopy * N.value + idx
  resetTimer()
}

// ── 边界复位 ──
watch(animatedIdx, (pos) => {
  const len = N.value
  if (len <= 1) return
  if (pos < len * 1.5) {
    jump(len)
  } else if (pos >= len * (COPIES - 1.5)) {
    jump(-len)
  }
})

// ── 自动轮播 ──
let timer: ReturnType<typeof setInterval> | null = null

function startTimer() {
  stopTimer()
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
  if (N.value <= 1) return
  timer = setInterval(goNext, props.interval)
}
function stopTimer() {
  if (timer !== null) {
    clearInterval(timer)
    timer = null
  }
}
function resetTimer() {
  stopTimer()
  startTimer()
}
function onMouseEnter() {
  stopTimer()
}
function onMouseLeave() {
  startTimer()
}

function updateSceneW() {
  sceneW.value = sceneRef.value?.offsetWidth ?? 800
}

onMounted(() => {
  updateSceneW()
  startTimer()
})
onBeforeUnmount(() => {
  stopTimer()
})
</script>

<template>
  <section class="ar-carousel-3d" @mouseenter="onMouseEnter" @mouseleave="onMouseLeave">
    <div ref="sceneRef" class="ar-carousel-3d__scene" :style="{ height: sceneH + 'px' }">
      <div class="ar-carousel-3d__mask-left" />
      <div class="ar-carousel-3d__mask-right" />

      <div class="ar-carousel-3d__stack">
        <div
          v-for="(item, i) in displayItems"
          :key="'c-' + i"
          class="ar-carousel-3d__card"
          :class="{ 'ar-carousel-3d__card--main': cardAtMain(i) }"
          :style="getStyle(i)"
          @click="handleCardClick(item, i)"
        >
          <slot
            name="card"
            :item="item"
            :index="i"
            :is-main="cardAtMain(i)"
            :show-overlay="showOverlay(i)"
          >
            <div class="ar-carousel-3d__fallback">{{ item }}</div>
          </slot>
        </div>
      </div>

      <button
        v-if="N > 1"
        class="ar-carousel-3d__nav ar-carousel-3d__nav--prev"
        aria-label="上一张"
        @click="goPrev"
      >
        <svg
          width="20"
          height="20"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2.5"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <polyline points="15 18 9 12 15 6" />
        </svg>
      </button>
      <button
        v-if="N > 1"
        class="ar-carousel-3d__nav ar-carousel-3d__nav--next"
        aria-label="下一张"
        @click="goNext"
      >
        <svg
          width="20"
          height="20"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2.5"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <polyline points="9 18 15 12 9 6" />
        </svg>
      </button>
    </div>

    <div v-if="N > 1" class="ar-carousel-3d__dots">
      <button
        v-for="(_, index) in items"
        :key="index"
        class="ar-carousel-3d__dot"
        :class="{ active: activeDot === index }"
        :aria-label="`切换到第 ${index + 1} 项`"
        type="button"
        @click="goTo(index)"
      >
        <span class="ar-carousel-3d__dot-fill" />
      </button>
    </div>
  </section>
</template>

<style scoped>
.ar-carousel-3d {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: var(--content-padding, 24px);
  overflow: hidden;
  user-select: none;
}

.ar-carousel-3d__scene {
  position: relative;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
}

.ar-carousel-3d__stack {
  position: absolute;
  left: 50%;
  top: 50%;
  width: 0;
  height: 0;
}

.ar-carousel-3d__card {
  position: absolute;
  left: 0;
  top: 0;
  width: v-bind(CARD_W + 'px');
  aspect-ratio: 4 / 3;
  border-radius: var(--radius-md);
  overflow: hidden;
  cursor: pointer;
  will-change: transform, opacity, filter;
  backface-visibility: hidden;
  -webkit-font-smoothing: antialiased;
}

.ar-carousel-3d__card:focus-visible {
  outline: 2px solid var(--primary-color);
  outline-offset: 2px;
}

.ar-carousel-3d__fallback {
  padding: 20px;
  color: var(--text-primary);
  font-size: 14px;
}

/* ── 遮罩 ── */
.ar-carousel-3d__mask-left,
.ar-carousel-3d__mask-right {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 40px;
  z-index: 100;
  pointer-events: none;
}

.ar-carousel-3d__mask-left {
  left: 0;
  background: linear-gradient(to right, var(--surface-color) 0%, transparent 100%);
}

.ar-carousel-3d__mask-right {
  right: 0;
  background: linear-gradient(to left, var(--surface-color) 0%, transparent 100%);
}

/* ── 导航 ── */
.ar-carousel-3d__nav {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  width: 36px;
  height: 36px;
  border-radius: var(--radius-full);
  border: 1px solid var(--border-color);
  background: color-mix(in srgb, var(--surface-color) 85%, transparent);
  backdrop-filter: blur(8px);
  color: var(--text-secondary);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 200;
  transition:
    background var(--transition-normal),
    color var(--transition-normal),
    transform var(--transition-normal);
  opacity: 0;
  pointer-events: none;
}

.ar-carousel-3d__scene:hover .ar-carousel-3d__nav {
  opacity: 1;
  pointer-events: auto;
}
.ar-carousel-3d__nav:hover {
  background: var(--surface-color);
  color: var(--primary-color);
  transform: translateY(-50%) scale(1.08);
}
.ar-carousel-3d__nav--prev {
  left: var(--spacing-md);
}
.ar-carousel-3d__nav--next {
  right: var(--spacing-md);
}

/* ── 指示点 ── */
.ar-carousel-3d__dots {
  display: flex;
  justify-content: center;
  gap: 10px;
}

.ar-carousel-3d__dot {
  width: 10px;
  height: 10px;
  border-radius: var(--radius-full);
  border: none;
  padding: 0;
  background: color-mix(in srgb, var(--primary-color) 26%, transparent);
  cursor: pointer;
  overflow: hidden;
  transition: transform var(--transition-normal);
}

.ar-carousel-3d__dot:hover {
  transform: scale(1.08);
}

.ar-carousel-3d__dot-fill {
  display: block;
  width: 100%;
  height: 100%;
  border-radius: inherit;
  background: color-mix(in srgb, var(--primary-color) 55%, transparent);
  transform: scale(0.65);
  transition: transform var(--transition-normal);
}

.ar-carousel-3d__dot.active .ar-carousel-3d__dot-fill {
  background: var(--primary-color);
  transform: scale(1);
}

@media (max-width: 680px) {
  .ar-carousel-3d__card {
    width: 200px;
  }
  .ar-carousel-3d__mask-left,
  .ar-carousel-3d__mask-right {
    width: 20px;
  }
}
</style>
