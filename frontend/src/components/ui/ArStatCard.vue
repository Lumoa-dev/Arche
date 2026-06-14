<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    /** 主数值 */
    value?: number | string
    /** 标签 */
    label?: string
    /** 副标题（如趋势百分比） */
    sublabel?: string
    /** 趋势方向 */
    trend?: 'up' | 'down' | 'neutral'
    /** 数值格式化 */
    formatter?: (val: number | string) => string
    /** 尺寸 */
    size?: 'sm' | 'md' | 'lg'
  }>(),
  {
    value: 0,
    label: '',
    sublabel: '',
    trend: 'neutral',
    formatter: undefined,
    size: 'md'
  }
)

const displayValue = computed(() => {
  if (props.formatter) return props.formatter(props.value)
  const num = typeof props.value === 'string' ? parseFloat(props.value) : props.value
  if (isNaN(num)) return props.value
  return num.toLocaleString()
})
</script>

<template>
  <ArCard variant="glass" class="ar-stat-card" :padding="size === 'sm' ? 'sm' : 'md'">
    <div class="ar-stat-card__inner">
      <div class="ar-stat-card__top">
        <span v-if="sublabel" class="ar-stat-card__sublabel" :class="`ar-stat-card__sublabel--${trend}`">
          <svg v-if="trend === 'up'" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round">
            <polyline points="18 15 12 9 6 15" />
          </svg>
          <svg v-else-if="trend === 'down'" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round">
            <polyline points="6 9 12 15 18 9" />
          </svg>
          {{ sublabel }}
        </span>
      </div>
      <span class="ar-stat-card__value" :class="`ar-stat-card__value--${size}`">{{ displayValue }}</span>
      <span class="ar-stat-card__label">{{ label }}</span>
    </div>
  </ArCard>
</template>

<style scoped>
.ar-stat-card {
  display: inline-flex;
  min-width: 120px;
}

.ar-stat-card__inner {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.ar-stat-card__top {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  min-height: 18px;
}

.ar-stat-card__sublabel {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  font-size: var(--text-xs);
  font-weight: var(--weight-medium);
  line-height: 1;
}

.ar-stat-card__sublabel--up { color: var(--color-success); }
.ar-stat-card__sublabel--down { color: var(--color-danger); }
.ar-stat-card__sublabel--neutral { color: var(--color-text-tertiary); }

.ar-stat-card__value {
  font-family: var(--font-mono);
  font-weight: var(--weight-bold);
  color: var(--color-text-primary);
  line-height: 1;
  font-variant-numeric: tabular-nums;
}

.ar-stat-card__value--sm { font-size: var(--text-xl); }
.ar-stat-card__value--md { font-size: var(--text-2xl); }
.ar-stat-card__value--lg { font-size: var(--text-3xl); }

.ar-stat-card__label {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
  line-height: 1;
}
</style>
