<script setup lang="ts">
/**
 * EditorBody — 编辑器正文区（可滚动+拖放插入）
 *
 * 包裹标题区、引言、段落卡片列表。
 * 支持从工具栏拖拽「插入」创建文本段落。
 * 横向间距由上层容器控制，此组件只负责纵向滚动和拖放。
 */
import { ref } from 'vue'
import type { ParagraphType } from '@/components/logic/useParagraphEditor'

defineSlots<{
  default: void
}>()

const emit = defineEmits<{
  dropParagraph: [type: ParagraphType]
}>()

const isDragOver = ref(false)
let dragEnterCount = 0

function handleDragEnter() {
  dragEnterCount++
  isDragOver.value = true
}

function handleDragLeave() {
  dragEnterCount--
  if (dragEnterCount <= 0) {
    dragEnterCount = 0
    isDragOver.value = false
  }
}

function handleDragOver(e: DragEvent) {
  e.preventDefault()
  if (e.dataTransfer) {
    e.dataTransfer.dropEffect = 'copy'
  }
}

function handleDrop(e: DragEvent) {
  isDragOver.value = false
  dragEnterCount = 0
  const type = e.dataTransfer?.getData('paragraph-type') as ParagraphType | undefined
  if (type) {
    emit('dropParagraph', type)
  }
}
</script>

<template>
  <div
    style="
      flex: 1;
      overflow-y: auto;
      padding: var(--spacing-md) var(--spacing-lg);
      max-width: 880px;
      width: 100%;
      margin: 0 auto;
      outline: 2px dashed transparent;
      outline-offset: -2px;
      transition: outline-color var(--transition-fast);
    "
    :style="{
      outlineColor: isDragOver ? 'var(--primary-color)' : 'transparent'
    }"
    @dragover.prevent="handleDragOver"
    @dragenter="handleDragEnter"
    @dragleave="handleDragLeave"
    @drop.prevent="handleDrop"
  >
    <slot />
  </div>
</template>
