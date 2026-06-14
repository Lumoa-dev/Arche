<script setup lang="ts">
/**
 * EditorIntroductionCard — 引言卡片（与段落卡片统一样式）
 *
 * 视觉上和段落卡片一致（同款 border/bg/圆角），但固定在标题下方
 * 不可拖拽排序（锚定位置）。
 */
import { ref, watch, onBeforeUnmount } from 'vue'
import { useEditor, EditorContent } from '@tiptap/vue-3'
import { StarterKit } from '@tiptap/starter-kit'
import { TextAlign } from '@tiptap/extension-text-align'
import { TextStyle } from '@tiptap/extension-text-style'

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
    TextAlign.configure({ types: ['paragraph'] })
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

function focusEditor() {
  editor.value?.commands.focus()
}

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
  <div class="intro-card">
    <div class="intro-card__label" @click="focusEditor">引言</div>
    <EditorContent :editor="editor" class="intro-card__editor" />
  </div>
</template>

<style scoped>
.intro-card {
  margin-bottom: var(--spacing-md);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-color);
  background: var(--surface-color, #fff);
  padding: 12px 16px;
}

.intro-card:hover {
  border-color: var(--border-hover-color, rgba(0, 0, 0, 0.12));
  box-shadow: var(--card-shadow-glass);
}

.intro-card__label {
  font-size: 11px;
  font-weight: var(--font-weight-semibold);
  color: var(--text-tertiary);
  letter-spacing: 0.06em;
  text-transform: uppercase;
  margin-bottom: var(--spacing-xs);
  user-select: none;
  cursor: pointer;
  transition: color var(--transition-fast);
}

.intro-card__label:hover {
  color: var(--text-secondary);
}

.intro-card__editor :deep(.ProseMirror) {
  min-height: 60px;
  font-size: 1.05em;
  line-height: 1.7;
  color: var(--text-secondary);
  font-family: var(--font-serif);
  outline: none;
}

.intro-card__editor :deep(.ProseMirror p) {
  margin: 0;
}
</style>
