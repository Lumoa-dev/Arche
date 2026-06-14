<script setup lang="ts">
/**
 * EditorIntroductionCard — 引言卡片（特殊卡片）
 *
 * KV 结构输入：每行一个 [Key] : [Value]。
 * 使用 ArCard outlined 作为容器。
 */
import ArVBox from '@/components/ui/ArVBox.vue'
import ArHBox from '@/components/ui/ArHBox.vue'
import ArCard from '@/components/ui/ArCard.vue'
import ArInput from '@/components/ui/ArInput.vue'
import ArButton from '@/components/ui/ArButton.vue'
import type { IntroductionEntry } from '@/components/logic/useParagraphEditor'

defineProps<{
  entries: IntroductionEntry[]
}>()

const emit = defineEmits<{
  addEntry: []
  removeEntry: [index: number]
  'update:entry': [index: number, field: 'key' | 'value', value: string]
}>()
</script>

<template>
  <ArCard variant="outlined" padding="md" style="margin: 0 var(--spacing-lg) var(--spacing-md)">
    <template #header>
      <span
        style="
          font-size: 13px;
          font-weight: var(--font-weight-semibold);
          color: var(--text-secondary);
        "
        >引言</span
      >
    </template>

    <ArVBox gap="8px">
      <ArHBox v-for="(entry, index) in entries" :key="`intro_${index}`" gap="6px">
        <ArInput
          :model-value="entry.key"
          placeholder="Key（可选）"
          size="sm"
          style="width: 140px"
          @update:model-value="emit('update:entry', index, 'key', $event)"
        />
        <span style="color: var(--text-tertiary); font-weight: var(--font-weight-bold)">:</span>
        <ArInput
          :model-value="entry.value"
          placeholder="Value"
          size="sm"
          style="flex: 1"
          @update:model-value="emit('update:entry', index, 'value', $event)"
        />
        <ArButton size="sm" type="ghost" @click="emit('removeEntry', index)"> × </ArButton>
      </ArHBox>

      <ArHBox style="padding-top: 4px; border-top: 1px dashed var(--border-color)">
        <ArButton size="sm" type="ghost" @click="emit('addEntry')"> + 添加条目 </ArButton>
      </ArHBox>
    </ArVBox>
  </ArCard>
</template>
