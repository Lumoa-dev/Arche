<script setup lang="ts">
/**
 * ArCard — 质感卡片
 *
 * Apple 风格多层级阴影设计，四档变体满足不同场景。
 * - glass:   磨玻璃通透感（默认），用于弹窗、浮层、编辑区
 * - elevated: 实底抬升，用于列表卡片、内容预览
 * - outlined: 描边轻量，用于表单内嵌区、引言
 * - plain:   无样式，完全交由父组件控制
 *
 * 可控 prop：variant / padding / hoverable / radius / shadow / disabled
 * 如需更精细调整，使用 CSS 变量覆盖（非违规手段）。
 */

import { computed } from 'vue'

type CardVariant = 'glass' | 'elevated' | 'outlined' | 'plain'
type CardPadding = 'none' | 'sm' | 'md' | 'lg'
type CardRadius = 'none' | 'sm' | 'md' | 'lg'
type CardShadow = 'none' | 'sm' | 'md' | 'lg'

const props = withDefaults(
  defineProps<{
    /** 卡片变体 */
    variant?: CardVariant
    /** 内边距 */
    padding?: CardPadding
    /** 圆角大小（默认随变体自动，可手动覆盖） */
    radius?: CardRadius
    /** 阴影强度（默认随变体自动，'none' 完全无阴影） */
    shadow?: CardShadow
    /** 悬停时轻微抬升 */
    hoverable?: boolean
    /** 禁用交互 */
    disabled?: boolean
  }>(),
  {
    variant: 'glass',
    padding: 'md',
    radius: 'md',
    shadow: undefined, // undefined = 按变体自动选择
    hoverable: false,
    disabled: false
  }
)

const emit = defineEmits<{
  click: [e: Event]
}>()

const resolvedShadow = computed(() => {
  if (props.shadow) return `ar-card--shadow-${props.shadow}`
  // 按变体自动选择默认阴影强度
  const map: Record<CardVariant, string> = {
    glass: 'ar-card--shadow-glass',
    elevated: 'ar-card--shadow-elevated',
    outlined: 'ar-card--shadow-outlined',
    plain: 'ar-card--shadow-none'
  }
  return map[props.variant]
})

const classes = computed(() => [
  'ar-card',
  `ar-card--${props.variant}`,
  `ar-card--pad-${props.padding}`,
  `ar-card--radius-${props.radius}`,
  resolvedShadow.value,
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
    <!-- 封面区（全宽，无内边距） -->
    <div v-if="$slots.cover" class="ar-card__cover">
      <slot name="cover" />
    </div>

    <!-- 顶栏（全宽） -->
    <div v-if="$slots.header" class="ar-card__header">
      <slot name="header" />
    </div>

    <!-- 主区域：左栏 | 内容区 | 右栏 -->
    <div v-if="$slots.left || $slots.default || $slots.right" class="ar-card__main">
      <div v-if="$slots.left" class="ar-card__left">
        <slot name="left" />
      </div>
      <div v-if="$slots.default" class="ar-card__body">
        <slot />
      </div>
      <div v-if="$slots.right" class="ar-card__right">
        <slot name="right" />
      </div>
    </div>

    <!-- 底栏（全宽） -->
    <div v-if="$slots.footer" class="ar-card__footer">
      <slot name="footer" />
    </div>
  </article>
</template>

<style scoped>
/* ════════════════════════════════════════
   ArCard — Apple 质感卡片
   设计要点：
   1. 三层阴影叠加 — 紧贴接触阴影 + 中距模糊 + 远距漫射
   2. 通透玻璃 / 实底抬升 / 轻描边 三档
   3. 圆角 + 内边距 + 阴影强度均可通过 prop 控制
   4. 禁止在组件内写具体色值，全走 CSS 变量
   ════════════════════════════════════════ */

/* ── 基础结构 ── */
.ar-card {
  position: relative;
  display: flex;
  flex-direction: column;
  transition:
    transform 0.2s var(--ease-out-spring),
    box-shadow 0.25s var(--ease-out-smooth),
    background 0.25s var(--ease-out-smooth);
  overflow: hidden;
}

/* ── 点击交互 ── */
.ar-card--clickable {
  cursor: pointer;
  touch-action: manipulation;
}
.ar-card--clickable:focus-visible {
  outline: 2px solid var(--primary-color);
  outline-offset: 2px;
}

/* ── disabled ── */
.ar-card--disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* ════════════════════════════════════════
   变体 1: glass — 磨玻璃通透感
   半透背景 + backdrop-filter + Apple 三层阴影
   适用于浮层、面板、编辑区域
   ════════════════════════════════════════ */
.ar-card--glass {
  background: var(--card-bg);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.6);
}

/* ════════════════════════════════════════
   变体 2: elevated — 实底抬升
   干净白底/灰底 + 多层阴影
   适用于列表卡片、内容预览
   ════════════════════════════════════════ */
.ar-card--elevated {
  background: var(--card-bg);
  border: 1px solid var(--border-color);
}

.ar-card--elevated.ar-card--hoverable:hover {
  background: var(--surface-strong-color);
}

/* ════════════════════════════════════════
   变体 3: outlined — 轻描边
   有极浅底色 + 微型阴影，不是只有框
   适用于内嵌区、引言、表单分组
   ════════════════════════════════════════ */
.ar-card--outlined {
  background: rgba(255, 255, 255, 0.35);
  border: 1px solid var(--border-color);
}

/* ════════════════════════════════════════
   变体 4: plain — 无样式
   完全交由父组件控制
   ════════════════════════════════════════ */
.ar-card--plain {
  background: none;
  border: none;
  border-radius: 0;
  overflow: visible;
}

/* ════════════════════════════════════════
   阴影档位 — Apple 三层叠加体系
   通过 prop shadow 控制，变体自动选择默认档位
   ════════════════════════════════════════ */

/* glass 默认阴影：极致轻薄 */
.ar-card--shadow-glass {
  box-shadow: var(--card-shadow-glass);
}

/* elevated 默认阴影：明显抬升 */
.ar-card--shadow-elevated {
  box-shadow: var(--card-shadow-elevated);
}

/* outlined 阴影：若有若无 */
.ar-card--shadow-outlined {
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
}

/* 无阴影 */
.ar-card--shadow-none {
  box-shadow: none;
}

/* ── 手动 shadow prop 档位 ── */
.ar-card--shadow-sm {
  box-shadow: var(--card-shadow-glass);
}
.ar-card--shadow-md {
  box-shadow: var(--card-shadow-elevated);
}
.ar-card--shadow-lg {
  box-shadow: var(--card-shadow-hover);
}

/* ── 悬停抬升（所有含阴影的变体通用） ── */
.ar-card--hoverable:hover {
  box-shadow: var(--card-shadow-hover);
  transform: translateY(-2px);
}

/* ════════════════════════════════════════
   圆角档位
   ════════════════════════════════════════ */
.ar-card--radius-none {
  border-radius: 0;
}
.ar-card--radius-sm {
  border-radius: var(--radius-sm);
}
.ar-card--radius-md {
  border-radius: var(--radius-lg);
}
.ar-card--radius-lg {
  border-radius: var(--radius-xl);
}

/* ════════════════════════════════════════
   内部区块 — 五区布局
   封面 > 顶栏 > (左栏 | 内容区 | 右栏) > 底栏
   ════════════════════════════════════════ */

.ar-card__cover {
  background: var(--card-bg-cover);
  line-height: 0;
  overflow: hidden;
  border-radius: inherit;
  border-bottom-left-radius: 0;
  border-bottom-right-radius: 0;
}

.ar-card__header {
  background: var(--card-bg-header);
  display: flex;
  align-items: center;
}

.ar-card__main {
  background: var(--card-bg-main);
  display: flex;
  flex-direction: row;
  min-width: 0;
}

.ar-card__left {
  background: var(--card-bg-left);
  flex-shrink: 0;
}

.ar-card__body {
  background: var(--card-bg-body);
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.ar-card__right {
  background: var(--card-bg-right);
  flex-shrink: 0;
}

.ar-card__footer {
  background: var(--card-bg-footer);
  display: flex;
  align-items: center;
  border-top: 1px solid var(--divider-color);
}

/* ════════════════════════════════════════
   内边距预设
   ════════════════════════════════════════ */
.ar-card--pad-none {
  --card-pad-body: 0;
  --card-pad-h: 0;
  --card-pad-v: 0;
}

.ar-card--pad-sm {
  --card-pad-body: var(--space-3);
  --card-pad-h: var(--space-3);
  --card-pad-v: var(--space-2);
}

.ar-card--pad-md {
  --card-pad-body: var(--space-4);
  --card-pad-h: var(--space-4);
  --card-pad-v: var(--space-3);
}

.ar-card--pad-lg {
  --card-pad-body: var(--space-6);
  --card-pad-h: var(--space-6);
  --card-pad-v: var(--space-4);
}

.ar-card__header {
  padding: var(--card-pad-v) var(--card-pad-h);
}
.ar-card__left {
  padding: var(--card-pad-body) 0 var(--card-pad-body) var(--card-pad-body);
}
.ar-card__body {
  padding: var(--card-pad-body);
}
.ar-card__right {
  padding: var(--card-pad-body) var(--card-pad-body) var(--card-pad-body) 0;
}
.ar-card__footer {
  padding: var(--card-pad-v) var(--card-pad-h);
}
</style>
