<script setup lang="ts">
/**
 * EditorToolbar — 编辑器顶部工具栏
 *
 * 与当前激活的 TipTap editor 实例联动，提供排版工具。
 * 纯 Ar 组件组合，无自定义 CSS。
 */
import ArHBox from '@/components/ui/ArHBox.vue'
import ArButton from '@/components/ui/ArButton.vue'
import ArSelect from '@/components/ui/ArSelect.vue'

defineProps<{
  hasActiveEditor: boolean
}>()

const fontSizeOptions = [
  { label: '正文', value: '0' },
  { label: '大', value: '1' },
  { label: '特大', value: '2' }
]
</script>

<template>
  <ArHBox
    gap="4px"
    wrap
    align="center"
    style="
      padding: 6px 12px;
      background: var(--surface-color);
      border-bottom: 1px solid var(--border-color);
      position: sticky;
      top: 0;
      z-index: 10;
    "
    :style="{
      opacity: hasActiveEditor ? 1 : 0.5,
      pointerEvents: hasActiveEditor ? 'auto' : 'none'
    }"
  >
    <ArHBox gap="2px">
      <ArButton size="sm" type="ghost" :disabled="!hasActiveEditor">
        <strong>B</strong>
      </ArButton>
      <ArButton size="sm" type="ghost" :disabled="!hasActiveEditor">
        <em>I</em>
      </ArButton>
      <ArButton size="sm" type="ghost" :disabled="!hasActiveEditor">
        <u>U</u>
      </ArButton>
    </ArHBox>

    <div style="width: 1px; height: 20px; background: var(--border-color); margin: 0 4px" />

    <ArSelect
      :model-value="'0'"
      :options="fontSizeOptions"
      :disabled="!hasActiveEditor"
      size="sm"
      style="width: 80px"
    />
  </ArHBox>
</template>
