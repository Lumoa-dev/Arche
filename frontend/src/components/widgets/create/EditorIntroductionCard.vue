<script setup lang="ts">
/**
 * EditorIntroductionCard — 引言卡片
 *
 * 与段落卡片区分：柔和底色 + 左侧朱砂装饰线 + 独特 header。
 * 使用 ArCard outlined 变体（增强后已有底色和微阴影）。
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
  <ArCard
    variant="outlined"
    padding="md"
    shadow="sm"
    style="
      margin-bottom: var(--spacing-md);
      background: var(--intro-card-bg, rgba(245, 235, 220, 0.35));
      border-left: 3px solid var(--primary-color);
      border-radius: var(--radius-md);
    "
  >
    <template #header>
      <div style="display: flex; align-items: center; gap: 8px">
        <!-- 小图标装饰 -->
        <svg
          width="14" height="14" viewBox="0 0 24 24"
          fill="none" stroke="var(--primary-color)"
          stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"
        >
          <circle cx="12" cy="12" r="10" />
          <line x1="12" y1="16" x2="12" y2="12" />
          <line x1="12" y1="8" x2="12.01" y2="8" />
        </svg>
        <span
          style="
            font-size: 13px;
            font-weight: var(--font-weight-semibold);
            color: var(--text-secondary);
          "
        >引言</span>
      </div>
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
        <span
          style="
            color: var(--text-tertiary);
            font-weight: var(--font-weight-bold);
            flex-shrink: 0;
          "
        >:</span>
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
