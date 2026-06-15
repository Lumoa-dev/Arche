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
import EditorSeparatorCard from './EditorSeparatorCard.vue'
import EditorHeadingCard from './EditorHeadingCard.vue'
import type { Editor } from '@tiptap/vue-3'
import type { EditorParagraph, ParagraphType } from '@/components/widgets/create/useParagraphEditor'

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
}>()

const isPreview = ref(false)

function onTypeChange(type: ParagraphType) {
  emit('update:type', props.paragraph.uid, type)
}

function togglePreview() {
  isPreview.value = !isPreview.value
}

function stripHtml(html: string): string {
  const div = document.createElement('div')
  div.innerHTML = html
  return div.textContent || ''
}

/** 解析段标题等级：'H2' → 2, 'H3' → 3 */
function parseLevel(heading?: string): number {
  if (!heading) return 2
  const m = heading.match(/H(\d)/)
  return m ? parseInt(m[1]!) : 2
}
</script>

<template>
  <div class="paragraph-card" :class="{ 'paragraph-card--preview': isPreview }">
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
              v-if="paragraph.type === 'text'"
              :uid="paragraph.uid"
              :model-value="paragraph.content"
              @update:model-value="emit('update:content', paragraph.uid, $event)"
              @ready="(ed: Editor) => emit('ready', paragraph.uid, ed)"
              @focus="(uid: string, ed: Editor) => emit('focus', uid, ed)"
            />
            <EditorHeadingCard
              v-else-if="paragraph.type === 'heading'"
              :content="paragraph.content"
              :level="parseLevel(paragraph.heading)"
              @update:content="emit('update:content', paragraph.uid, $event)"
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
            <EditorSeparatorCard v-else-if="paragraph.type === 'separator'" />
            <div
              v-else-if="paragraph.type === 'table'"
              style="padding: 24px; text-align: center; color: var(--text-tertiary)"
            >
              表格编辑（即将支持）
            </div>
          </template>

          <!-- 预览模式 -->
          <template v-else>
            <div class="paragraph-preview">
              <p v-if="paragraph.type === 'text'">
                {{ stripHtml(paragraph.content) || '（空段落）' }}
              </p>
              <div v-else-if="paragraph.type === 'heading'" class="paragraph-preview__heading">
                {{ paragraph.content || '（空标题）' }}
              </div>
              <div v-else-if="paragraph.type === 'image'" class="preview-media">
                <img v-if="paragraph.media_url" :src="paragraph.media_url" alt="" />
                <span v-else>（图片占位）</span>
              </div>
              <div v-else-if="paragraph.type === 'video'" class="preview-media">
                <span>{{ paragraph.media_url ? '🎬 视频' : '（视频占位）' }}</span>
              </div>
              <code v-else-if="paragraph.type === 'code'">{{
                paragraph.content || '（代码块）'
              }}</code>
              <span v-else-if="paragraph.type === 'separator'">━━━ 分隔线 ━━━</span>
              <span v-else>{{ '（' + paragraph.type + '）' }}</span>
            </div>
          </template>
        </div>
      </div>
    </div>

    <!-- 右侧拖拽轨道（窄条，悬停浮现） -->
    <div class="drag-rail" title="拖拽排序">
      <!-- 手柄图标（竖直六点） -->
      <svg
        class="drag-rail__icon"
        width="12"
        height="20"
        viewBox="0 0 12 20"
        fill="none"
        stroke="currentColor"
        stroke-width="1.5"
        stroke-linecap="round"
      >
        <circle cx="3" cy="4" r="1.5" fill="currentColor" stroke="none" />
        <circle cx="9" cy="4" r="1.5" fill="currentColor" stroke="none" />
        <circle cx="3" cy="10" r="1.5" fill="currentColor" stroke="none" />
        <circle cx="9" cy="10" r="1.5" fill="currentColor" stroke="none" />
        <circle cx="3" cy="16" r="1.5" fill="currentColor" stroke="none" />
        <circle cx="9" cy="16" r="1.5" fill="currentColor" stroke="none" />
      </svg>
      <!-- 轨道装饰线（拖拽时浮现） -->
      <div class="drag-rail__track" />
    </div>
  </div>
</template>

<style scoped>
.paragraph-card {
  display: flex;
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

.paragraph-card--preview {
  background: var(--surface-hover-color, rgba(128, 128, 128, 0.03));
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

/* ── 拖拽轨道（右侧窄条） ── */

.drag-rail {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 20px;
  flex-shrink: 0;
  cursor: grab;
  color: var(--text-tertiary);
  border-left: 1px solid transparent;
  border-radius: 0 var(--radius-md) var(--radius-md) 0;
  user-select: none;
  transition:
    color var(--transition-fast),
    background var(--transition-fast),
    border-color var(--transition-fast),
    width var(--transition-fast);
}

/* 默认隐藏，只有 hover 卡片时才露出 */
.drag-rail__icon {
  opacity: 0;
  transition: opacity var(--transition-fast);
}

.drag-rail__track {
  position: absolute;
  top: 4px;
  bottom: 4px;
  left: 50%;
  width: 2px;
  transform: translateX(-50%);
  background: transparent;
  border-radius: 1px;
  transition: background var(--transition-fast);
}

.paragraph-card:hover .drag-rail {
  border-left-color: var(--border-color);
  background: var(--surface-hover-color);
}

.paragraph-card:hover .drag-rail__icon {
  opacity: 0.5;
}

.drag-rail:hover .drag-rail__icon {
  opacity: 0.8;
  color: var(--text-primary);
}

.drag-rail:active {
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
