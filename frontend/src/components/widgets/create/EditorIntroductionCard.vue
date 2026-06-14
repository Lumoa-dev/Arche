<script setup lang="ts">
/**
 * EditorIntroductionCard — 引言编辑区
 *
 * 从 KV 数组改为富文本编辑。设计上摒弃了「卡片」概念，
 * 以流动式 inline 编辑区呈现，视觉上"长"在标题与正文之间。
 * 使用轻量 TipTap 编辑，与段落编辑器共享排版能力。
 */
import { watch, onBeforeUnmount } from 'vue'
import { useEditor, EditorContent } from '@tiptap/vue-3'
import { StarterKit } from '@tiptap/starter-kit'
import { TextAlign } from '@tiptap/extension-text-align'
import { TextStyle } from '@tiptap/extension-text-style'
import { Placeholder } from '@tiptap/extension-placeholder'

const props = defineProps<{
  modelValue: string
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

const editor = useEditor({
  content: props.modelValue || '',
  extensions: [
    StarterKit.configure({
      heading: { levels: [1, 2, 3] },
      codeBlock: false,
      blockquote: false
    }),
    TextStyle,
    TextAlign.configure({ types: ['paragraph'] }),
    Placeholder.configure({
      placeholder: '写一段引言……简要概括文章的核心观点'
    })
  ],
  editorProps: {
    attributes: {
      class: 'intro-editor'
    }
  },
  onUpdate: ({ editor: ed }) => {
    const html = ed.getHTML()
    if (html !== props.modelValue) {
      emit('update:modelValue', html)
    }
  }
})

watch(
  () => props.modelValue,
  (val) => {
    if (editor.value && val !== editor.value.getHTML()) {
      editor.value.commands.setContent(val || '', false)
    }
  }
)

onBeforeUnmount(() => {
  editor.value?.destroy()
})
</script>

<template>
  <div class="intro-section">
    <!-- 轻标签：纯文字标识 -->
    <div class="intro-label">引言</div>
    <!-- 编辑区：无边框无背景，flow 在文档流中 -->
    <EditorContent :editor="editor" class="intro-editor-wrapper" />
  </div>
</template>

<style scoped>
.intro-section {
  margin-bottom: var(--spacing-lg);
  padding: var(--spacing-sm) 0;
}

.intro-label {
  font-size: 12px;
  font-weight: var(--font-weight-semibold);
  color: var(--text-tertiary);
  letter-spacing: 0.06em;
  text-transform: uppercase;
  margin-bottom: var(--spacing-xs);
  user-select: none;
}

.intro-editor-wrapper {
  /* 编辑器本身是 flow 布局，不产生额外卡片效应 */
}

.intro-editor-wrapper :deep(.ProseMirror) {
  min-height: 60px;
  padding: var(--spacing-sm) 0;
  font-size: 1.05em;
  line-height: 1.7;
  color: var(--text-secondary);
  font-family: var(--font-serif);
  outline: none;
}

.intro-editor-wrapper :deep(.ProseMirror p) {
  margin: 0;
}

.intro-editor-wrapper :deep(.ProseMirror p.is-editor-empty:first-child::before) {
  color: var(--text-quaternary);
  content: attr(data-placeholder);
  float: left;
  height: 0;
  pointer-events: none;
}
</style>
