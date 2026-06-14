<script setup lang="ts">
/**
 * AddParagraphButton — 添加段落按钮
 *
 * 固定在段落列表底部，点击弹出类型选择或直接添加文本段落。
 */
import ArHBox from '@/components/ui/ArHBox.vue'
import ArCard from '@/components/ui/ArCard.vue'
import ArButton from '@/components/ui/ArButton.vue'
import type { ParagraphType } from '@/components/logic/useParagraphEditor'

defineEmits<{
  add: [type: ParagraphType]
}>()

const quickTypes: { label: string; type: ParagraphType }[] = [
  { label: '文本', type: 'text' },
  { label: '标题', type: 'heading' },
  { label: '图片', type: 'image' },
  { label: '代码', type: 'code' },
  { label: '分隔线', type: 'separator' }
]
</script>

<template>
  <ArCard variant="outlined" padding="md" style="margin: 0 var(--spacing-lg) var(--spacing-xl)">
    <ArHBox gap="12px" justify="center" align="center">
      <ArButton size="sm" type="primary" @click="$emit('add', 'text')"> + 添加段落 </ArButton>
      <ArHBox gap="4px">
        <ArButton
          v-for="item in quickTypes"
          :key="item.type"
          size="sm"
          type="ghost"
          @click="$emit('add', item.type)"
        >
          {{ item.label }}
        </ArButton>
      </ArHBox>
    </ArHBox>
  </ArCard>
</template>
