<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { NIcon } from 'naive-ui'
import {
  HeartOutline,
  Heart,
  BookmarkOutline,
  Bookmark,
  ShareSocialOutline
} from '@vicons/ionicons5'

withDefaults(
  defineProps<{
    liked?: boolean
    favorited?: boolean
    likeCount?: number
    disabled?: boolean
  }>(),
  {
    liked: false,
    favorited: false,
    likeCount: 0,
    disabled: false
  }
)

const emit = defineEmits<{
  toggleLike: []
  toggleFavorite: []
  share: []
}>()

const barX = ref(0)
const visible = ref(false)
const side = ref<'left' | 'right'>('left')

let contentRect: DOMRect | null = null
let ticking = false
let barTop = 0

const BAR_WIDTH = 52
const BAR_GAP = 20
const DEAD_ZONE = 60

function updatePosition(e: MouseEvent) {
  if (!contentRect) return

  const mouseX = e.clientX
  const cx = contentRect.left + contentRect.width / 2
  const offsetFromCenter = mouseX - cx

  if (Math.abs(offsetFromCenter) < DEAD_ZONE) return

  if (offsetFromCenter > 0) {
    barX.value = contentRect.right + BAR_GAP
    side.value = 'right'
  } else {
    barX.value = contentRect.left - BAR_WIDTH - BAR_GAP
    side.value = 'left'
  }
  visible.value = true
}

function onMouseMove(e: MouseEvent) {
  if (!ticking) {
    window.requestAnimationFrame(() => {
      updatePosition(e)
      ticking = false
    })
    ticking = true
  }
}

function onMouseLeave() {
  visible.value = false
}

function recalc() {
  const wrapper = document.querySelector('.content-wrapper')
  const authorBar = document.querySelector('.author-bar')
  if (wrapper) {
    contentRect = wrapper.getBoundingClientRect()
    const anchorTop = authorBar ? authorBar.getBoundingClientRect().top : contentRect.top - 45
    barTop = Math.max(anchorTop, 80)
  }
}

onMounted(() => {
  recalc()
  const wrapper = document.querySelector('.content-wrapper')
  if (wrapper) {
    const ro = new ResizeObserver(recalc)
    ro.observe(wrapper)
  }
  document.addEventListener('mousemove', onMouseMove)
  document.addEventListener('mouseleave', onMouseLeave)
})

onUnmounted(() => {
  document.removeEventListener('mousemove', onMouseMove)
  document.removeEventListener('mouseleave', onMouseLeave)
})
</script>

<template>
  <Transition name="fade">
    <div
      v-show="visible"
      :class="['floating-actions', `floating-actions--${side}`, { 'is-disabled': disabled }]"
      :style="{ left: barX + 'px', top: barTop + 'px' }"
    >
      <button
        class="action-btn like-btn"
        :class="{ 'is-active': liked }"
        :disabled="disabled"
        :aria-label="liked ? '取消点赞' : '点赞'"
        @click="emit('toggleLike')"
      >
        <NIcon size="22">
          <component :is="liked ? Heart : HeartOutline" />
        </NIcon>
        <span v-if="likeCount > 0" class="action-count">{{ likeCount }}</span>
      </button>

      <button
        class="action-btn fav-btn"
        :class="{ 'is-active': favorited }"
        :disabled="disabled"
        :aria-label="favorited ? '取消收藏' : '收藏'"
        @click="emit('toggleFavorite')"
      >
        <NIcon size="22">
          <component :is="favorited ? Bookmark : BookmarkOutline" />
        </NIcon>
      </button>

      <button
        class="action-btn share-btn"
        :disabled="disabled"
        aria-label="分享"
        @click="emit('share')"
      >
        <NIcon size="22">
          <ShareSocialOutline />
        </NIcon>
      </button>
    </div>
  </Transition>
</template>

<style scoped>
.floating-actions {
  position: fixed;
  z-index: 10;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 8px 6px;
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  transition: opacity 0.15s ease;
}

.floating-actions--left::after {
  content: '';
  position: absolute;
  right: -6px;
  top: 50%;
  margin-top: -5px;
  width: 10px;
  height: 10px;
  background: var(--surface-color);
  border-right: 1px solid var(--border-color);
  border-top: 1px solid var(--border-color);
  transform: rotate(45deg);
}

.floating-actions--right::after {
  content: '';
  position: absolute;
  left: -6px;
  top: 50%;
  margin-top: -5px;
  width: 10px;
  height: 10px;
  background: var(--surface-color);
  border-left: 1px solid var(--border-color);
  border-bottom: 1px solid var(--border-color);
  transform: rotate(45deg);
}

.floating-actions.is-disabled {
  opacity: 0.6;
}

.action-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  padding: 8px 6px;
  border: none;
  background: transparent;
  cursor: pointer;
  color: var(--text-tertiary);
  border-radius: var(--radius-md);
  transition:
    color var(--transition-fast),
    background-color var(--transition-fast),
    transform var(--transition-fast);
  font-family: var(--font-sans);
  touch-action: manipulation;
}

.action-btn:hover:not(:disabled) {
  background: var(--surface-hover-color);
}

.action-btn:active:not(:disabled) {
  transform: scale(0.9);
}

.action-btn:disabled {
  cursor: not-allowed;
  opacity: 0.4;
}

.action-count {
  font-size: 11px;
  font-weight: var(--font-weight-semibold);
  font-variant-numeric: tabular-nums;
  line-height: 1;
}

.like-btn.is-active {
  color: var(--accent-red);
}

.like-btn:hover:not(:disabled) {
  color: var(--accent-red);
}

.fav-btn.is-active {
  color: var(--accent-yellow);
}

.fav-btn:hover:not(:disabled) {
  color: var(--accent-yellow);
}

.share-btn:hover:not(:disabled) {
  color: var(--primary-color);
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
