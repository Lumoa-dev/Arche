<script setup lang="ts">
/**
 * CardToolbar — 段落卡片操作条（悬停浮现）
 *
 * 卡片顶部操作栏：类型切换 | 上移 | 下移 | 删除。
 * 默认透明，悬停/聚焦时浮现，减少视觉噪声。
 */
import ArHBox from '@/components/ui/ArHBox.vue'
import ArButton from '@/components/ui/ArButton.vue'
import ArSelect from '@/components/ui/ArSelect.vue'
import type { ParagraphType } from '@/components/logic/useParagraphEditor'

defineProps<{
  type: ParagraphType
  canMoveUp: boolean
  canMoveDown: boolean
}>()

const emit = defineEmits<{
  'update:type': [type: ParagraphType]
  moveUp: []
  moveDown: []
  delete: []
}>()

const typeOptions: { label: string; value: ParagraphType }[] = [
  { label: '文本', value: 'text' },
  { label: '标题', value: 'heading' },
  { label: '图片', value: 'image' },
  { label: '视频', value: 'video' },
  { label: '代码', value: 'code' },
  { label: '表格', value: 'table' }
]
</script>

<template>
  <div>
    <ArHBox gap="8px" justify="space-between" align="center">
      <ArHBox gap="4px">
        <ArSelect
          :model-value="type"
          :options="typeOptions"
          size="sm"
          style="width: 92px"
          @update:model-value="emit('update:type', $event as ParagraphType)"
        />
      </ArHBox>

      <ArHBox gap="4px">
        <ArButton size="sm" type="ghost" :disabled="!canMoveUp" @click="emit('moveUp')"> ↑ </ArButton>
        <ArButton size="sm" type="ghost" :disabled="!canMoveDown" @click="emit('moveDown')"> ↓ </ArButton>
        <ArButton size="sm" type="ghost" @click="emit('delete')"> × </ArButton>
      </ArHBox>
    </ArHBox>
  </div>
</template>

<style scoped>
</style>
