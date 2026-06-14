<script setup lang="ts">
/**
 * EditorParagraphCard — 段落卡片（无卡片边框 + 拖拽排序）
 *
 * 去掉了 ArCard 的玻璃/阴影风格，段落直接"长"在纸面上。
 * 支持 HTML5 拖拽排序（draggable + drop 事件）。
 * 控制栏默认隐藏，悬停/聚焦时浮现。
 */
import { ref } from 'vue'
import CardToolbar from './CardToolbar.vue'
import RichTextEditor from './RichTextEditor.vue'
import EditorImageUploader from './EditorImageUploader.vue'
import EditorVideoUrlInput from './EditorVideoUrlInput.vue'
import EditorCodeEditor from './EditorCodeEditor.vue'
import type { Editor } from '@tiptap/vue-3'
import type { EditorParagraph, ParagraphType } from '@/components/logic/useParagraphEditor'

const props = defineProps<{
  paragraph: EditorParagraph
  canMoveUp: boolean
  canMoveDown: boolean
}>()

const emit = defineEmits<{
  'update:type': [uid: string, type: ParagraphType]
  moveUp: [uid: string]
  moveDown: [uid: string]
  delete: [uid: string]
  'update:content': [uid: string, content: string]
  'update:mediaUrl': [uid: string, url: string]
  'update:caption': [uid: string, caption: string]
  ready: [uid: string, editor: Editor]
  focus: [uid: string, editor: Editor]
  /** 拖拽：将此段落放置到目标段落位置 */
  dropOn: [draggedUid: string, targetUid: string]
}>()

const isDragOver = ref(false)

function onTypeChange(type: ParagraphType) {
  emit('update:type', props.paragraph.uid, type)
}

function handleDragStart(e: DragEvent) {
  e.dataTransfer?.setData('text/plain', props.paragraph.uid)
  if (e.dataTransfer) {
    e.dataTransfer.effectAllowed = 'move'
  }
}

function handleDragOver(e: DragEvent) {
  e.preventDefault()
  if (e.dataTransfer) {
    e.dataTransfer.dropEffect = 'move'
  }
  isDragOver.value = true
}

function handleDragLeave() {
  isDragOver.value = false
}

function handleDrop(e: DragEvent) {
  e.preventDefault()
  isDragOver.value = false
  const draggedUid = e.dataTransfer?.getData('text/plain')
  if (draggedUid && draggedUid !== props.paragraph.uid) {
    emit('dropOn', draggedUid, props.paragraph.uid)
  }
}
</script>

<template>
  <div
    class="paragraph-block"
    :class="{ 'paragraph-block--drag-over': isDragOver }"
    draggable="true"
    @dragstart="handleDragStart"
    @dragover="handleDragOver"
    @dragleave="handleDragLeave"
    @drop="handleDrop"
  >
    <div class="paragraph-controls">
      <CardToolbar
        :type="paragraph.type"
        :can-move-up="canMoveUp"
        :can-move-down="canMoveDown"
        @update:type="onTypeChange"
        @move-up="emit('moveUp', paragraph.uid)"
        @move-down="emit('moveDown', paragraph.uid)"
        @delete="emit('delete', paragraph.uid)"
      />
    </div>

    <div class="paragraph-content">
      <!-- 文本 / 标题 -->
      <RichTextEditor
        v-if="paragraph.type === 'text' || paragraph.type === 'heading'"
        :uid="paragraph.uid"
        :model-value="paragraph.content"
        @update:model-value="emit('update:content', paragraph.uid, $event)"
        @ready="(ed: Editor) => emit('ready', paragraph.uid, ed)"
        @focus="(uid: string, ed: Editor) => emit('focus', uid, ed)"
      />

      <!-- 图片 -->
      <EditorImageUploader
        v-else-if="paragraph.type === 'image'"
        :media-url="paragraph.media_url || ''"
        :caption="paragraph.caption || ''"
        @update:media-url="emit('update:mediaUrl', paragraph.uid, $event)"
        @update:caption="emit('update:caption', paragraph.uid, $event)"
      />

      <!-- 视频 -->
      <EditorVideoUrlInput
        v-else-if="paragraph.type === 'video'"
        :media-url="paragraph.media_url || ''"
        @update:media-url="emit('update:mediaUrl', paragraph.uid, $event)"
      />

      <!-- 代码 -->
      <EditorCodeEditor
        v-else-if="paragraph.type === 'code'"
        :content="paragraph.content"
        @update:content="emit('update:content', paragraph.uid, $event)"
      />

      <!-- 分隔线 -->
      <div v-else-if="paragraph.type === 'separator'" style="padding: 12px 24px">
        <hr style="border: none; border-top: 1px solid var(--border-color); margin: 0" />
      </div>

      <!-- 表格（占位） -->
      <div
        v-else-if="paragraph.type === 'table'"
        style="padding: 24px; text-align: center; color: var(--text-tertiary)"
      >
        表格编辑（即将支持）
      </div>
    </div>
  </div>
</template>

<style scoped>
.paragraph-block {
  position: relative;
  margin-bottom: var(--spacing-md);
  border-radius: var(--radius-sm);
  transition: background var(--transition-fast), outline-color var(--transition-fast);
  outline: 2px solid transparent;
  outline-offset: -2px;
}

.paragraph-block:hover {
  background: var(--surface-hover-color, rgba(128, 128, 128, 0.03));
}

.paragraph-block--drag-over {
  outline-color: var(--primary-color);
  background: var(--primary-light-color, rgba(102, 126, 234, 0.06));
}

.paragraph-controls {
  opacity: 0;
  transition: opacity 0.15s ease;
}

.paragraph-block:hover .paragraph-controls,
.paragraph-block:focus-within .paragraph-controls {
  opacity: 1;
}
</style>
