<script setup lang="ts">
/**
 * EditorTitleArea — 标题区域（固定在编辑器顶部）
 *
 * 主标题 + 不限数量的副标题，通过 [+] 添加副标题行。
 * 不像卡片，直接"长"在页面上。
 */
import ArVBox from '@/components/ui/ArVBox.vue'
import ArHBox from '@/components/ui/ArHBox.vue'
import ArInput from '@/components/ui/ArInput.vue'
import ArButton from '@/components/ui/ArButton.vue'

defineProps<{
  title: string
  subtitles: string[]
}>()

const emit = defineEmits<{
  'update:title': [value: string]
  'update:subtitle': [index: number, value: string]
  addSubtitle: []
  removeSubtitle: [index: number]
}>()
</script>

<template>
  <ArVBox
    gap="var(--spacing-sm)"
    style="
      padding: var(--spacing-lg) 0 var(--spacing-md);
      border-bottom: 1px solid var(--border-color);
      margin-bottom: var(--spacing-md);
    "
  >
    <!-- 主标题 -->
    <ArInput
      :model-value="title"
      placeholder="输入文章标题……"
      size="lg"
      :maxlength="120"
      show-count
      @update:model-value="emit('update:title', $event)"
    />

    <!-- 副标题列表 -->
    <ArVBox v-if="subtitles.length > 0" gap="6px">
      <ArHBox v-for="(sub, index) in subtitles" :key="`sub_${index}`" gap="6px">
        <ArInput
          :model-value="sub"
          :placeholder="`副标题 ${index + 1}`"
          :maxlength="200"
          style="flex: 1"
          @update:model-value="emit('update:subtitle', index, $event)"
        />
        <ArButton size="sm" type="ghost" @click="emit('removeSubtitle', index)"> × </ArButton>
      </ArHBox>
    </ArVBox>

    <!-- 添加副标题：文字左 + 号右 -->
    <ArHBox justify="space-between" align="center">
      <span style="font-size: 13px; color: var(--text-tertiary)">添加副标题</span>
      <ArButton size="sm" type="ghost" @click="emit('addSubtitle')"> + </ArButton>
    </ArHBox>
  </ArVBox>
</template>
