<script setup lang="ts">
import { computed } from 'vue'

type DateSeparator = '-' | '/'

const props = withDefaults(
  defineProps<{
    /** 年（显示年份时必传） */
    year?: number
    /** 月（1-12） */
    month?: number
    /** 日（1-31） */
    day?: number
    /** 时（0-23） */
    hour?: number
    /** 分（0-59） */
    minute?: number
    /** 秒（0-59） */
    second?: number
    /** 毫秒（0-999） */
    ms?: number
    /** 日期部分分隔符 */
    dateSeparator?: DateSeparator
    /** 是否隐藏年份 */
    hideYear?: boolean
    /** 是否隐藏月份 */
    hideMonth?: boolean
    /** 是否隐藏日 */
    hideDay?: boolean
    /** 是否隐藏小时 */
    hideHour?: boolean
    /** 是否隐藏分钟 */
    hideMinute?: boolean
    /** 是否隐藏秒 */
    hideSecond?: boolean
    /** 是否隐藏毫秒 */
    hideMs?: boolean
  }>(),
  {
    year: undefined,
    month: undefined,
    day: undefined,
    hour: undefined,
    minute: undefined,
    second: undefined,
    ms: undefined,
    dateSeparator: '-',
    hideYear: false,
    hideMonth: false,
    hideDay: false,
    hideHour: false,
    hideMinute: false,
    hideSecond: false,
    hideMs: false
  }
)

/** 补零到指定位数 */
function pad(n: number | undefined, len = 2): string | null {
  if (n === undefined || n === null) return null
  return String(n).padStart(len, '0')
}

/** 日期片段 */
const dateParts = computed(() => {
  const parts: string[] = []
  if (!props.hideYear) { const v = pad(props.year, 4); if (v) parts.push(v) }
  if (!props.hideMonth) { const v = pad(props.month); if (v) parts.push(v) }
  if (!props.hideDay) { const v = pad(props.day); if (v) parts.push(v) }
  return parts
})

/** 时间片段 */
const timeParts = computed(() => {
  const parts: string[] = []
  if (!props.hideHour) { const v = pad(props.hour); if (v) parts.push(v) }
  if (!props.hideMinute) { const v = pad(props.minute); if (v) parts.push(v) }
  if (!props.hideSecond) { const v = pad(props.second); if (v) parts.push(v) }
  return parts
})

const hasDate = computed(() => dateParts.value.length > 0)
const hasTime = computed(() => timeParts.value.length > 0)
const hasMs = computed(() => !props.hideMs && props.ms !== undefined && props.ms !== null)

/** 最终的文字内容 */
const displayText = computed(() => {
  const parts: string[] = []
  if (hasDate.value) parts.push(dateParts.value.join(props.dateSeparator))
  if (hasTime.value) parts.push(timeParts.value.join(':'))
  const text = parts.join(' ')
  if (hasMs.value) return `${text}.${pad(props.ms, 3)}`
  return text
})
</script>

<template>
  <time class="ar-time" :datetime="displayText" :title="displayText">
    {{ displayText }}
  </time>
</template>

<style scoped>
.ar-time {
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
  line-height: 1;
  white-space: nowrap;
  user-select: none;
}
</style>
