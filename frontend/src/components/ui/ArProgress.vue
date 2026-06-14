<script setup lang="ts">
import { computed } from 'vue'

type ProgressVariant = 'inline' | 'top'

const props = withDefaults(
  defineProps<{
    /** 变体：inline 页面内嵌 / top 页面顶栏 */
    variant?: ProgressVariant
    /** 进度百分比（0-100），不传时显示脉冲动画（indeterminate） */
    percent?: number
    /** 是否正在加载（top 变体专用） */
    loading?: boolean
    /** 进度条高度（inline 默认 8px，top 默认 3px） */
    height?: number
    /** 自定义颜色 */
    color?: string
  }>(),
  {
    variant: 'inline',
    percent: -1,
    loading: false,
    height: undefined,
    color: undefined
  }
)

const barHeight = computed(() => {
  if (props.height !== undefined) return props.height
  return props.variant === 'top' ? 3 : 8
})

const isIndeterminate = computed(() => props.percent < 0 || props.percent === undefined)
const clampedPercent = computed(() => Math.min(100, Math.max(0, props.percent)))

const barColor = computed(() => props.color || 'var(--color-accent)')

const classes = computed(() => [
  'ar-progress',
  `ar-progress--${props.variant}`,
  {
    'ar-progress--loading': props.loading || (props.variant === 'top' && isIndeterminate.value),
    'ar-progress--indeterminate': isIndeterminate.value && props.variant !== 'top'
  }
])

const barStyle = computed(
  () =>
    ({
      height: `${barHeight.value}px`,
      '--progress-color': barColor.value
    }) as Record<string, string>
)

const fillStyle = computed(() => {
  if (isIndeterminate.value) return {}
  return { width: `${clampedPercent.value}%` }
})
</script>

<template>
  <!-- ═══ top 变体：贴顶细条 ═══ -->
  <div
    v-if="variant === 'top'"
    :class="classes"
    :style="barStyle"
    role="progressbar"
    :aria-valuenow="percent"
    aria-valuemin="0"
    aria-valuemax="100"
  >
    <div
      class="ar-progress__fill"
      :class="{ 'ar-progress__fill--indeterminate': isIndeterminate || loading }"
      :style="fillStyle"
    />
  </div>

  <!-- ═══ inline 变体：左插槽 + 进度条 + 右插槽 ═══ -->
  <div
    v-else
    :class="classes"
    role="progressbar"
    :aria-valuenow="percent"
    aria-valuemin="0"
    aria-valuemax="100"
  >
    <!-- 左容器 -->
    <div v-if="$slots.left" class="ar-progress__side ar-progress__side--left">
      <slot name="left" />
    </div>

    <!-- 进度条 -->
    <div class="ar-progress__bar" :style="barStyle">
      <div
        class="ar-progress__fill"
        :class="{ 'ar-progress__fill--indeterminate': isIndeterminate }"
        :style="fillStyle"
      >
        <!-- 脉冲光效 -->
        <span v-if="!isIndeterminate && percent > 0" class="ar-progress__pulse" />
      </div>
    </div>

    <!-- 右容器 -->
    <div v-if="$slots.right" class="ar-progress__side ar-progress__side--right">
      <slot name="right" />
    </div>
  </div>
</template>

<style scoped>
/* ════════════════════════════════════════
   ArProgress — 双形态进度条
   top: 贴顶细条，用于页面加载
   inline: 内嵌布局，左右插槽 + 中间脉冲动画
   ════════════════════════════════════════ */

/* ── top 变体：固定到视口顶部 ── */
.ar-progress--top {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 9999;
  background: transparent;
  overflow: hidden;
  pointer-events: none;
}

.ar-progress--top .ar-progress__fill {
  height: 100%;
  background: var(--progress-color, var(--color-accent));
  transition: width 0.3s ease;
  border-radius: 0;
}

/* top 加载动画 — 像 "嗖" 一下冲过去 */
.ar-progress--top .ar-progress__fill--indeterminate {
  width: 30% !important;
  animation: ar-progress-sweep 1.5s ease-in-out infinite;
}

@keyframes ar-progress-sweep {
  0% {
    transform: translateX(-100%);
  }
  100% {
    transform: translateX(400%);
  }
}

/* ── inline 变体：横向三栏布局 ── */
.ar-progress--inline {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  width: 100%;
}

/* ── 左右插槽 ── */
.ar-progress__side {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  flex-shrink: 0;
  font-family: var(--font-sans);
  font-size: var(--text-xs);
  color: var(--color-text-secondary);
  line-height: 1;
}

.ar-progress__side--left {
  justify-content: flex-end;
}

.ar-progress__side--right {
  justify-content: flex-start;
}

/* ── 进度条轨道 ── */
.ar-progress__bar {
  position: relative;
  flex: 1;
  min-width: 40px;
  background: var(--color-bg-muted);
  border-radius: var(--radius-full);
  overflow: hidden;
}

/* ── 已填充部分 ── */
.ar-progress__fill {
  height: 100%;
  background: var(--progress-color, var(--color-accent));
  border-radius: var(--radius-full);
  transition: width 0.4s var(--ease-out-smooth);
  position: relative;
}

/* indeterminate 脉冲动画 */
.ar-progress--indeterminate .ar-progress__fill--indeterminate {
  width: 40% !important;
  animation: ar-progress-indeterminate 1.8s ease-in-out infinite;
  border-radius: var(--radius-full);
}

@keyframes ar-progress-indeterminate {
  0% {
    transform: translateX(-100%);
  }
  50% {
    transform: translateX(150%);
  }
  100% {
    transform: translateX(350%);
  }
}

/* ── 脉冲光效（呼吸闪烁） ── */
.ar-progress__pulse {
  position: absolute;
  inset: 0;
  background: linear-gradient(
    90deg,
    transparent 0%,
    rgba(255, 255, 255, 0.35) 50%,
    transparent 100%
  );
  animation: ar-progress-pulse 2s ease-in-out infinite;
  border-radius: inherit;
}

@keyframes ar-progress-pulse {
  0% {
    opacity: 0;
  }
  50% {
    opacity: 1;
  }
  100% {
    opacity: 0;
  }
}

/* ── 动画优先：减少动效时关闭 ── */
@media (prefers-reduced-motion: reduce) {
  .ar-progress__fill--indeterminate,
  .ar-progress__pulse {
    animation: none !important;
  }
}
</style>
