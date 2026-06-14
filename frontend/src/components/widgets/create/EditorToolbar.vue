<script setup lang="ts">
/**
 * EditorToolbar — 纸面内嵌工具栏
 *
 * 位于纸面（EditorBody）顶部，与正文内容构成一体。
 * 无 sticky 无通栏背景，融入纸面色。
 */
import ArHBox from '@/components/ui/ArHBox.vue'
import ArButton from '@/components/ui/ArButton.vue'
import type { ParagraphType } from '@/components/logic/useParagraphEditor'
import {
  ListOutline,
  ColorPaletteOutline,
  ImageOutline,
  VideocamOutline,
  CodeSlashOutline,
  RemoveOutline,
  SaveOutline,
  SendOutline,
  ChatbubbleOutline
} from '@/icons'

defineProps<{
  hasActiveEditor: boolean
  saving: boolean
  isEdit: boolean
  execCommand: (cmd: string) => void
}>()

const emit = defineEmits<{
  insert: [type: ParagraphType]
  insertSeparator: []
  toggleCover: []
  saveDraft: []
  publish: []
  cancel: []
}>()

/** 拖拽插入：给 dataTransfer 写入段落类型 */
function handleDragStart(type: ParagraphType, e: DragEvent) {
  e.dataTransfer?.setData('text/plain', `paragraph:${type}`)
  if (e.dataTransfer) e.dataTransfer.effectAllowed = 'copy'
}
</script>

<template>
  <div class="paper-toolbar">
    <!-- ── 左侧：格式化 ── -->
    <div class="toolbar-group">
      <!-- 加粗 -->
      <ArButton
        size="xs"
        type="ghost"
        icon
        title="加粗"
        :disabled="!hasActiveEditor"
        @click="execCommand('toggleBold')"
      >
        <template #icon>
          <svg
            width="15"
            height="15"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2.2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <path d="M6 4h6a4 4 0 1 1 0 8H6z" />
            <path d="M6 12h7a4 4 0 1 1 0 8H6z" />
          </svg>
        </template>
      </ArButton>
      <!-- 斜体 -->
      <ArButton
        size="xs"
        type="ghost"
        icon
        title="斜体"
        :disabled="!hasActiveEditor"
        @click="execCommand('toggleItalic')"
      >
        <template #icon>
          <svg
            width="15"
            height="15"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2.2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <line x1="17" y1="6" x2="10" y2="18" />
            <line x1="19" y1="6" x2="14" y2="6" />
            <line x1="10" y1="18" x2="5" y2="18" />
          </svg>
        </template>
      </ArButton>
      <!-- 下划线 -->
      <ArButton
        size="xs"
        type="ghost"
        icon
        title="下划线"
        :disabled="!hasActiveEditor"
        @click="execCommand('toggleUnderline')"
      >
        <template #icon>
          <svg
            width="15"
            height="15"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2.2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <path d="M6 4v6a6 6 0 0 0 12 0V4" />
            <line x1="4" y1="20" x2="20" y2="20" />
          </svg>
        </template>
      </ArButton>
      <!-- 删除线 -->
      <ArButton
        size="xs"
        type="ghost"
        icon
        title="删除线"
        :disabled="!hasActiveEditor"
        @click="execCommand('toggleStrike')"
      >
        <template #icon>
          <svg
            width="15"
            height="15"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2.2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <path d="M6 5c0-1 .7-2 2-2h8c1.3 0 2 1 2 2" />
            <path d="M18 12H6" />
            <path d="M16 19c0 1-.7 2-2 2H9c-1.3 0-2-1-2-2" />
          </svg>
        </template>
      </ArButton>
      <!-- 行内代码 -->
      <ArButton
        size="xs"
        type="ghost"
        icon
        title="行内代码"
        :disabled="!hasActiveEditor"
        @click="execCommand('toggleCode')"
      >
        <template #icon>
          <svg
            width="15"
            height="15"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <polyline points="16 18 22 12 16 6" />
            <polyline points="8 6 2 12 8 18" />
          </svg>
        </template>
      </ArButton>
      <!-- 文字颜色 -->
      <ArButton
        size="xs"
        type="ghost"
        icon
        title="文字颜色"
        :disabled="!hasActiveEditor"
        @click="execCommand('setColor')"
      >
        <template #icon><ColorPaletteOutline /></template>
      </ArButton>
    </div>

    <div class="separator" />

    <!-- ── 对齐与列表 ── -->
    <div class="toolbar-group">
      <ArButton
        size="xs"
        type="ghost"
        icon
        title="左对齐"
        :disabled="!hasActiveEditor"
        @click="execCommand('setTextAlignLeft')"
      >
        <template #icon>
          <svg
            width="15"
            height="15"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
          >
            <line x1="3" y1="6" x2="21" y2="6" />
            <line x1="3" y1="10" x2="15" y2="10" />
            <line x1="3" y1="14" x2="19" y2="14" />
            <line x1="3" y1="18" x2="13" y2="18" />
          </svg>
        </template>
      </ArButton>
      <ArButton
        size="xs"
        type="ghost"
        icon
        title="居中"
        :disabled="!hasActiveEditor"
        @click="execCommand('setTextAlignCenter')"
      >
        <template #icon>
          <svg
            width="15"
            height="15"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
          >
            <line x1="3" y1="6" x2="21" y2="6" />
            <line x1="5" y1="10" x2="19" y2="10" />
            <line x1="3" y1="14" x2="21" y2="14" />
            <line x1="6" y1="18" x2="18" y2="18" />
          </svg>
        </template>
      </ArButton>
      <ArButton
        size="xs"
        type="ghost"
        icon
        title="右对齐"
        :disabled="!hasActiveEditor"
        @click="execCommand('setTextAlignRight')"
      >
        <template #icon>
          <svg
            width="15"
            height="15"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
          >
            <line x1="3" y1="6" x2="21" y2="6" />
            <line x1="9" y1="10" x2="21" y2="10" />
            <line x1="5" y1="14" x2="21" y2="14" />
            <line x1="11" y1="18" x2="21" y2="18" />
          </svg>
        </template>
      </ArButton>
      <ArButton
        size="xs"
        type="ghost"
        icon
        title="引用"
        :disabled="!hasActiveEditor"
        @click="execCommand('toggleBlockquote')"
      >
        <template #icon><ChatbubbleOutline /></template>
      </ArButton>
      <ArButton
        size="xs"
        type="ghost"
        icon
        title="无序列表"
        :disabled="!hasActiveEditor"
        @click="execCommand('toggleBulletList')"
      >
        <template #icon><ListOutline /></template>
      </ArButton>
      <ArButton
        size="xs"
        type="ghost"
        icon
        title="有序列表"
        :disabled="!hasActiveEditor"
        @click="execCommand('toggleOrderedList')"
      >
        <template #icon>
          <svg
            width="15"
            height="15"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
          >
            <line x1="9" y1="6" x2="21" y2="6" />
            <line x1="9" y1="12" x2="21" y2="12" />
            <line x1="9" y1="18" x2="21" y2="18" />
            <text x="3" y="9" font-size="8" font-weight="bold" fill="currentColor">1</text>
            <text x="3" y="15" font-size="8" font-weight="bold" fill="currentColor">2</text>
            <text x="3" y="21" font-size="8" font-weight="bold" fill="currentColor">3</text>
          </svg>
        </template>
      </ArButton>
    </div>

    <div class="separator" />

    <!-- ── 插入 ── -->
    <div class="toolbar-group">
      <span draggable="true" @dragstart="handleDragStart('text', $event)" style="display:inline-flex" title="拖拽插入段落">
        <ArButton size="xs" type="ghost" icon title="插入段落" :disabled="!hasActiveEditor" @click="emit('insert', 'text')">
          <template #icon>
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M12 5v14" /><path d="M5 12h14" />
            </svg>
          </template>
        </ArButton>
      </span>
      <span draggable="true" @dragstart="handleDragStart('image', $event)" style="display:inline-flex" title="拖拽插入图片">
        <ArButton size="xs" type="ghost" icon title="插入图片" @click="emit('insert', 'image')">
          <template #icon><ImageOutline /></template>
        </ArButton>
      </span>
      <span draggable="true" @dragstart="handleDragStart('video', $event)" style="display:inline-flex" title="拖拽插入视频">
        <ArButton size="xs" type="ghost" icon title="插入视频" @click="emit('insert', 'video')">
          <template #icon><VideocamOutline /></template>
        </ArButton>
      </span>
      <span draggable="true" @dragstart="handleDragStart('code', $event)" style="display:inline-flex" title="拖拽插入代码块">
        <ArButton size="xs" type="ghost" icon title="插入代码块" @click="emit('insert', 'code')">
          <template #icon><CodeSlashOutline /></template>
        </ArButton>
      </span>
      <span draggable="true" @dragstart="handleDragStart('separator', $event)" style="display:inline-flex" title="拖拽插入分隔线">
        <ArButton size="xs" type="ghost" icon title="插入分隔线" @click="emit('insertSeparator')">
          <template #icon><RemoveOutline /></template>
        </ArButton>
      </span>
      <ArButton size="xs" type="ghost" icon title="设置封面" @click="emit('toggleCover')">
        <template #icon>
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2.2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
            <circle cx="8.5" cy="8.5" r="1.5" />
            <polyline points="21 15 16 10 5 21" />
          </svg>
        </template>
      </ArButton>
    </div>

    <!-- ── 右侧：操作 ── -->
    <div class="toolbar-spacer" />
    <div class="toolbar-actions">
      <ArButton
        size="sm"
        type="secondary"
        :loading="saving"
        @click="emit('saveDraft')"
        title="存草稿"
        style="gap: 2px"
      >
        <template #icon><SaveOutline /></template>
        存稿
      </ArButton>
      <ArButton
        size="sm"
        type="primary"
        :loading="saving"
        @click="emit('publish')"
        title="发布"
        style="gap: 2px"
      >
        <template #icon><SendOutline /></template>
        {{ isEdit ? '保存' : '发送' }}
      </ArButton>
      <ArButton size="sm" type="ghost" @click="emit('cancel')" title="取消">取消</ArButton>
    </div>
  </div>
</template>

<style scoped>
.paper-toolbar {
  user-select: none;
  padding: 0 0 var(--spacing-sm);
  margin-bottom: var(--spacing-md);
  border-bottom: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  gap: 4px;
}

.toolbar-group {
  display: flex;
  align-items: center;
  gap: 2px;
}

.separator {
  width: 1px;
  height: 24px;
  background: var(--divider-color);
  margin: 0 6px;
  flex-shrink: 0;
}

.toolbar-spacer {
  flex: 1;
}

.toolbar-actions {
  display: flex;
  align-items: center;
  gap: 6px;
}
</style>
