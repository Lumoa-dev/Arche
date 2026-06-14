<script setup lang="ts">
/**
 * EditorParagraphCard — 通用段落卡片
 *
 * 使用 ArCard（glass 变体）作为容器，
 * 玻璃通透感+微阴影，在纸面上形成第二层浮层。
 */
import ArCard from '@/components/ui/ArCard.vue'
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
}>()

function onTypeChange(type: ParagraphType) {
  emit('update:type', props.paragraph.uid, type)
}
</script>

<template>
  <ArCard variant="glass" padding="none" shadow="sm">
    <template #header>
      <CardToolbar
        :type="paragraph.type"
        :can-move-up="canMoveUp"
        :can-move-down="canMoveDown"
        @update:type="onTypeChange"
        @move-up="emit('moveUp', paragraph.uid)"
        @move-down="emit('moveDown', paragraph.uid)"
        @delete="emit('delete', paragraph.uid)"
      />
    </template>

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
  </ArCard>
</template>
