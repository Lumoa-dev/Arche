<script setup lang="ts">
/**
 * EditorParagraphCard — 段落卡片（可见轻卡片 + 拖拽手柄 + 预览）
 *
 * 有可见的卡片边框和悬浮态，但比之前的 glass 风格更克制。
 * 左侧拖拽手柄（仅上下拖拽），右侧浮出控制栏含预览切换按钮。
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
  dropOn: [draggedUid: string, targetUid: string]
}>()

const isDragOver = ref(false)
const isDragging = ref(false)
const isPreview = ref(false)

function onTypeChange(type: ParagraphType) {
  emit('update:type', props.paragraph.uid, type)
}

function togglePreview() {
  isPreview.value = !isPreview.value
}

/* ── 拖拽 ── */

function handleDragStart(e: DragEvent) {
  e.dataTransfer?.setData('text/plain', props.paragraph.uid)
  if (e.dataTransfer) e.dataTransfer.effectAllowed = 'move'
  isDragging.value = true
}

function handleDragEnd() {
  isDragging.value = false
  isDragOver.value = false
}

function handleDragOver(e: DragEvent) {
  e.preventDefault()
  if (e.dataTransfer) e.dataTransfer.dropEffect = 'move'
  isDragOver.value = true
}

function handleDragLeave() {
  isDragOver.value = false
}

function handleDrop(e: DragEvent) {
  e.preventDefault()
  isDragOver.value = false
  isDragging.value = false
  const draggedUid = e.dataTransfer?.getData('text/plain')
  if (draggedUid && draggedUid !== props.paragraph.uid) {
    emit('dropOn', draggedUid, props.paragraph.uid)
  }
}

function stripHtml(html: string): string {
  const div = document.createElement('div')
  div.innerHTML = html
  return div.textContent || ''
}
</script>

<template>
  <div
    class="paragraph-card"
    :class="{
      'paragraph-card--drag-over': isDragOver,
      'paragraph-card--dragging': isDragging,
      'paragraph-card--preview': isPreview
    }"
  >
    <!-- 拖拽放置指示线（悬停时显示） -->
    <div v-if="isDragOver" class="drop-indicator">
      <span class="drop-indicator__label">移动到此</span>
    </div>

    <!-- 卡片主体（flex row: 内容区 + 右侧操作栏） -->
    <div class="paragraph-card__inner">
      <!-- 内容区 -->
      <div class="paragraph-card__content">
        <div class="paragraph-controls">
          <CardToolbar
            :type="paragraph.type"
            :can-move-up="canMoveUp"
            :can-move-down="canMoveDown"
            :preview="isPreview"
            @update:type="onTypeChange"
            @move-up="emit('moveUp', paragraph.uid)"
            @move-down="emit('moveDown', paragraph.uid)"
            @delete="emit('delete', paragraph.uid)"
            @toggle-preview="togglePreview"
          />
        </div>

        <div class="paragraph-body">
          <template v-if="!isPreview">
            <RichTextEditor
              v-if="paragraph.type === 'text' || paragraph.type === 'heading'"
              :uid="paragraph.uid"
              :model-value="paragraph.content"
              @update:model-value="emit('update:content', paragraph.uid, $event)"
              @ready="(ed: Editor) => emit('ready', paragraph.uid, ed)"
              @focus="(uid: string, ed: Editor) => emit('focus', uid, ed)"
            />
          <EditorImageUploader
            v-else-if="paragraph.type === 'image'"
            :media-url="paragraph.media_url || ''"
            :caption="paragraph.caption || ''"
            @update:media-url="emit('update:mediaUrl', paragraph.uid, $event)"
            @update:caption="emit('update:caption', paragraph.uid, $event)"
          />
          <EditorVideoUrlInput
            v-else-if="paragraph.type === 'video'"
            :media-url="paragraph.media_url || ''"
            @update:media-url="emit('update:mediaUrl', paragraph.uid, $event)"
          />
          <EditorCodeEditor
            v-else-if="paragraph.type === 'code'"
            :content="paragraph.content"
            @update:content="emit('update:content', paragraph.uid, $event)"
          />
          <div v-else-if="paragraph.type === 'separator'" style="padding: 12px 24px">
            <hr style="border: none; border-top: 1px solid var(--border-color); margin: 0" />
          </div>
          <div v-else-if="paragraph.type === 'table'" style="padding: 24px; text-align: center; color: var(--text-tertiary)">
            表格编辑（即将支持）
          </div>
        </template>

        <!-- 预览模式 -->
        <template v-else>
          <div class="paragraph-preview">
            <p v-if="paragraph.type === 'text' || paragraph.type === 'heading'">
              {{ stripHtml(paragraph.content) || '（空段落）' }}
            </p>
            <div v-else-if="paragraph.type === 'image'" class="preview-media">
              <img v-if="paragraph.media_url" :src="paragraph.media_url" alt="" />
              <span v-else>（图片占位）</span>
            </div>
            <div v-else-if="paragraph.type === 'video'" class="preview-media">
              <span>{{ paragraph.media_url ? '🎬 视频' : '（视频占位）' }}</span>
            </div>
            <code v-else-if="paragraph.type === 'code'">{{ paragraph.content || '（代码块）' }}</code>
            <span v-else-if="paragraph.type === 'separator'">━━━ 分隔线 ━━━</span>
            <span v-else>{{ '（' + paragraph.type + '）' }}</span>
          </div>
        </template>
      </div>
    </div>

    <!-- 右侧拖拽手柄 -->
    <div
      class="drag-handle"
      draggable="true"
      title="拖拽排序"
      @dragstart="handleDragStart"
      @dragend="handleDragEnd"
    >
      <svg width="14" height="18" viewBox="0 0 14 18" fill="currentColor" opacity="0.35">
        <circle cx="4" cy="3" r="1.5" /><circle cx="10" cy="3" r="1.5" />
        <circle cx="4" cy="9" r="1.5" /><circle cx="10" cy="9" r="1.5" />
        <circle cx="4" cy="15" r="1.5" /><circle cx="10" cy="15" r="1.5" />
      </svg>
    </div>
  </div>
</template>

<style scoped>
.paragraph-card {
  position: relative;
  margin-bottom: var(--spacing-md);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-color);
  background: var(--surface-color, #fff);
  transition:
    border-color var(--transition-fast),
    box-shadow var(--transition-fast),
    opacity var(--transition-fast);
}

.paragraph-card:hover {
  border-color: var(--border-hover-color, rgba(0, 0, 0, 0.12));
  box-shadow: var(--card-shadow-glass);
}

.paragraph-card--dragging {
  opacity: 0.4;
}

.paragraph-card--drag-over {
  border-color: var(--primary-color);
  box-shadow: var(--card-shadow-glass);
  /* 「开合」效果：被悬停的卡片上方让出空间给指示线 */
  padding-top: 32px;
  transition:
    padding-top 0.2s ease,
    border-color var(--transition-fast),
    box-shadow var(--transition-fast);
}

.paragraph-card--preview {
  background: var(--surface-hover-color, rgba(128, 128, 128, 0.03));
}

/* ── 放置指示线 ── */

.drop-indicator {
  position: absolute;
  top: -1px;
  left: -1px;
  right: -1px;
  display: flex;
  align-items: center;
  gap: 8px;
  pointer-events: none;
  z-index: 5;
}

.drop-indicator::before,
.drop-indicator::after {
  content: '';
  flex: 1;
  height: 2px;
  background: var(--primary-color);
  border-radius: 1px;
}

.drop-indicator__label {
  font-size: 11px;
  font-weight: var(--font-weight-semibold);
  color: var(--primary-color);
  background: var(--surface-color);
  padding: 0 8px;
  white-space: nowrap;
  border-radius: var(--radius-sm);
  line-height: 22px;
}

/* ── 卡片内部布局 ── */

.paragraph-card__inner {
  display: flex;
  flex: 1;
  min-width: 0;
}

.paragraph-card__content {
  flex: 1;
  min-width: 0;
}

/* ── 拖拽手柄（右侧） ── */

.drag-handle {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  flex-shrink: 0;
  cursor: grab;
  color: var(--text-tertiary);
  transition: color var(--transition-fast), background var(--transition-fast);
  border-left: 1px solid var(--border-color);
  border-radius: 0 var(--radius-md) var(--radius-md) 0;
  user-select: none;
}

.drag-handle:hover {
  color: var(--text-primary);
  background: var(--surface-hover-color);
}

.drag-handle:active {
  cursor: grabbing;
}

/* ── 控制栏 ── */

.paragraph-controls {
  opacity: 0;
  transition: opacity 0.15s ease;
  padding: 4px 8px 0;
}

.paragraph-card:hover .paragraph-controls,
.paragraph-card:focus-within .paragraph-controls {
  opacity: 1;
}

.paragraph-body {
  /* 编辑器内容区 */
}

/* ── 预览内容 ── */

.paragraph-preview {
  padding: 12px 16px;
  min-height: 40px;
  font-family: var(--font-serif);
  font-size: 14px;
  line-height: 1.7;
  color: var(--text-secondary);
}

.paragraph-preview p {
  margin: 0;
}

.paragraph-preview code {
  display: block;
  padding: 12px;
  background: var(--surface-hover-color);
  border-radius: var(--radius-sm);
  font-family: var(--font-mono);
  font-size: 13px;
  white-space: pre-wrap;
}

.paragraph-preview .preview-media {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 80px;
  background: var(--surface-hover-color);
  border-radius: var(--radius-sm);
  color: var(--text-tertiary);
  font-size: 13px;
}

.paragraph-preview .preview-media img {
  max-width: 100%;
  max-height: 200px;
  object-fit: contain;
  border-radius: var(--radius-sm);
}
</style>
