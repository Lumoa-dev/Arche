<script setup lang="ts">
/**
 * RichTextEditor — TipTap 富文本编辑器封装
 *
 * 段落卡片内部的富文本编辑区。提供基本的排版能力，通过 emit 与父组件同步。
 * 顶部工具栏由 EditorToolbar 统一提供，通过 TipTap 的 editor 实例联动。
 *
 * 注意：TipTap v3 的 useEditor 返回 ShallowRef<Editor | undefined>，
 * 所有对 editor 的访问必须通过 .value。
 */
import { watch, onBeforeUnmount } from 'vue'
import { useEditor, EditorContent, type Editor } from '@tiptap/vue-3'
import { StarterKit } from '@tiptap/starter-kit'
import { TextAlign } from '@tiptap/extension-text-align'
import { TextStyle } from '@tiptap/extension-text-style'
import { FontFamily } from '@tiptap/extension-font-family'
import { Color } from '@tiptap/extension-color'
import { Image } from '@tiptap/extension-image'

const props = defineProps<{
  modelValue: string
  placeholder?: string
  uid?: string // 段落 uid，用于焦点追踪
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string]
  ready: [editor: Editor]
  focus: [uid: string, editor: Editor]
}>()

const editor = useEditor({
  content: props.modelValue || '',
  extensions: [
    StarterKit.configure({
      heading: { levels: [1, 2, 3, 4] },
      codeBlock: false
    }),
    TextStyle,
    FontFamily,
    Color,
    TextAlign.configure({ types: ['heading', 'paragraph'] }),
    Image.configure({ inline: false })
  ],
  editorProps: {
    attributes: {
      class: 'rich-text-editor'
    }
  },
  onUpdate: ({ editor: ed }) => {
    const html = ed.getHTML()
    emit('update:modelValue', html)
  },
  onSelectionUpdate: ({ editor: ed }) => {
    // 选中变化 = 编辑器获得焦点，通知父组件
    if (props.uid) {
      emit('focus', props.uid, ed as any)
    }
  },
  onCreate: ({ editor: ed }) => {
    emit('ready', ed as any)
  }
})

watch(
  () => props.modelValue,
  (val) => {
    const ed = editor.value
    if (ed && val !== ed.getHTML()) {
      ed.commands.setContent(val || '', { emitUpdate: false })
    }
  }
)

onBeforeUnmount(() => {
  editor.value?.destroy()
})

defineExpose({ editor })
</script>

<template>
  <div class="rich-text-wrapper">
    <EditorContent v-if="editor" :editor="editor" />
  </div>
</template>

<style scoped>
.rich-text-wrapper {
  min-height: 60px;
  padding: 8px 12px;
  line-height: 1.8;
}

.rich-text-wrapper :deep(.ProseMirror) {
  outline: none;
  min-height: 40px;
  font-family: var(--font-serif);
  font-size: 15px;
  color: var(--text-primary);
}

.rich-text-wrapper :deep(.ProseMirror p) {
  margin: 0.3em 0;
}

.rich-text-wrapper :deep(.ProseMirror p.is-editor-empty:first-child::before) {
  color: var(--text-quaternary);
  content: attr(data-placeholder);
  float: left;
  height: 0;
  pointer-events: none;
}
</style>
