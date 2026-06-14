<script setup lang="ts">
import { computed } from 'vue'

type CardVariant = 'glass' | 'elevated' | 'outlined' | 'plain'
type CardPadding = 'none' | 'sm' | 'md' | 'lg'

const props = withDefaults(
  defineProps<{
    /** 卡片变体 — glass 是默认的磨玻璃效果 */
    variant?: CardVariant
    /** 内边距 */
    padding?: CardPadding
    /** 是否可悬停（悬停时轻微抬升） */
    hoverable?: boolean
    /** 是否禁用交互 */
    disabled?: boolean
  }>(),
  {
    variant: 'glass',
    padding: 'md',
    hoverable: false,
    disabled: false
  }
)

const emit = defineEmits<{
  click: [e: Event]
}>()

const classes = computed(() => [
  'ar-card',
  `ar-card--${props.variant}`,
  `ar-card--pad-${props.padding}`,
  {
    'ar-card--hoverable': props.hoverable && !props.disabled,
    'ar-card--disabled': props.disabled,
    'ar-card--clickable': !props.disabled
  }
])

function handleClick(e: Event) {
  if (props.disabled) return
  emit('click', e)
}

function handleKeydown(e: KeyboardEvent) {
  if (props.disabled) return
  emit('click', e)
}
</script>

<template>
  <article
    :class="classes"
    :aria-disabled="disabled || undefined"
    :tabindex="disabled ? undefined : 0"
    role="article"
    @click="handleClick"
    @keydown.enter="handleClick"
    @keydown.space.prevent="handleClick"
  >
    <!-- 封面区（可选） -->
    <div v-if="$slots.cover" class="ar-card__cover">
      <slot name="cover" />
    </div>

    <!-- 内容区 -->
    <div v-if="$slots.default" class="ar-card__body">
      <slot />
    </div>

    <!-- 底部（可选） -->
    <div v-if="$slots.footer" class="ar-card__footer">
      <slot name="footer" />
    </div>
  </article>
</template>

<style scoped>
/* ════════════════════════════════════════
   ArCard — 磨玻璃质感卡片
   设计意图：轻盈、通透、有层次
   与背景噪声纹理配合产生微妙互动
   ════════════════════════════════════════ */

/* ── 基础结构 ── */
.ar-card {
  position: relative;
  display: flex;
  flex-direction: column;
  border-radius: var(--radius-lg);
  transition:
    transform var(--transition-normal),
    box-shadow var(--transition-normal),
    background var(--transition-normal);
  /* 防止 backdrop-filter 溢出圆角 */
  overflow: hidden;
}

/* ── 点击交互 ── */
.ar-card--clickable {
  cursor: pointer;
  touch-action: manipulation;
}
.ar-card--clickable:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
}

/* ── disabled ── */
.ar-card--disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* ════════════════════════════════════════
   变体 1: glass — 默认磨玻璃
   接近不透明，但透出背景质感
   关键在 backdrop-filter 与背景噪声纹理的互动
   ════════════════════════════════════════ */
.ar-card--glass {
  background: rgba(255, 255, 255, 0.88);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border: 1px solid rgba(255, 255, 255, 0.65);
  box-shadow:
    0 1px 3px rgba(45, 40, 34, 0.06),
    0 1px 2px rgba(45, 40, 34, 0.04);
}

.ar-card--glass:hover {
  box-shadow:
    0 4px 12px rgba(45, 40, 34, 0.08),
    0 2px 4px rgba(45, 40, 34, 0.06);
}

.ar-card--glass.ar-card--hoverable:hover {
  transform: translateY(-2px);
  box-shadow:
    0 8px 24px rgba(45, 40, 34, 0.1),
    0 4px 8px rgba(45, 40, 34, 0.06);
}

/* ════════════════════════════════════════
   变体 2: elevated — 实色抬升
   适用于内容密集场景，纯粹的 elevation 感
   ════════════════════════════════════════ */
.ar-card--elevated {
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border);
  box-shadow: var(--shadow-sm);
}

.ar-card--elevated:hover {
  box-shadow: var(--shadow-md);
}

.ar-card--elevated.ar-card--hoverable:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-lg);
}

/* ════════════════════════════════════════
   变体 3: outlined — 轻描边
   最克制，只有边框勾勒
   ════════════════════════════════════════ */
.ar-card--outlined {
  background: transparent;
  border: 1px solid var(--color-border);
  box-shadow: none;
}

.ar-card--outlined.ar-card--hoverable:hover {
  border-color: var(--color-accent);
}

/* ════════════════════════════════════════
   变体 4: plain — 无样式
   完全交给父组件控制
   ════════════════════════════════════════ */
.ar-card--plain {
  background: none;
  border: none;
  box-shadow: none;
  border-radius: 0;
  overflow: visible;
}

/* ════════════════════════════════════════
   内部区块
   ════════════════════════════════════════ */

/* 封面区 — 顶部，无内边距，撑满宽度 */
.ar-card__cover {
  line-height: 0;
  /* 确保封面图片不会溢出圆角 */
  overflow: hidden;
  border-radius: var(--radius-lg) var(--radius-lg) 0 0;
}

/* 内容区 */
.ar-card__body {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

/* 底部 — 带分隔线 */
.ar-card__footer {
  display: flex;
  align-items: center;
  border-top: 1px solid var(--color-border-light);
}

/* ════════════════════════════════════════
   内边距预设
   ════════════════════════════════════════ */
.ar-card--pad-none .ar-card__body { padding: 0; }
.ar-card--pad-none .ar-card__footer { padding: 0; }

.ar-card--pad-sm .ar-card__body { padding: var(--space-3); }
.ar-card--pad-sm .ar-card__footer { padding: var(--space-2) var(--space-3); }

.ar-card--pad-md .ar-card__body { padding: var(--space-4); }
.ar-card--pad-md .ar-card__footer { padding: var(--space-3) var(--space-4); }

.ar-card--pad-lg .ar-card__body { padding: var(--space-6); }
.ar-card--pad-lg .ar-card__footer { padding: var(--space-4) var(--space-6); }
</style>
