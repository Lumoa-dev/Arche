<script setup lang="ts">
/**
 * EditorBody — 编辑器正文区（纸面 + 可滚动 + 拖放插入）
 *
 * Apple Notes 式纸面布局：居中纸面 + 阴影，与背景形成「桌面-纸张」层次。
 * 横向间距由纸面内边距控制，此组件只负责纸面容器 + 纵向滚动 + 拖放。
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
  <!-- 外层的「桌面」区域 — 负责滚动 -->
  <div
    class="editor-desk"
    @dragover.prevent="handleDragOver"
    @dragenter="handleDragEnter"
    @dragleave="handleDragLeave"
    @drop.prevent="handleDrop"
  >
    <!-- 内层的「纸面」— 居中、白底、阴影 -->
    <div class="editor-paper" :class="{ 'editor-paper--drag-over': isDragOver }">
      <slot />
    </div>
  </div>
</template>

<style scoped>
.editor-desk {
  /* 桌面背景延续页面渐变 */
}

.editor-paper {
  max-width: 880px;
  width: 100%;
  margin: var(--spacing-lg) auto;
  padding: var(--spacing-lg) var(--spacing-xl);
  min-height: calc(100vh - 120px);
  background: var(--paper-color);
  box-shadow: var(--paper-shadow);
  border-radius: var(--radius-lg);
  transition:
    box-shadow var(--transition-normal),
    outline-color var(--transition-fast);
  outline: 2px dashed transparent;
  outline-offset: -2px;
}

.editor-paper--drag-over {
  outline-color: var(--primary-color);
}
</style>
