<script setup lang="ts">
/**
 * editor.vue — 单编辑器页面
 *
 * 全页单 TipTap 富文本编辑器，0 CSS。
 * 布局：工具栏 → 封面预览 → 标题区 → 富文本正文
 */
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useEditor, EditorContent } from '@tiptap/vue-3'
import { StarterKit } from '@tiptap/starter-kit'
import { TextAlign } from '@tiptap/extension-text-align'
import { TextStyle } from '@tiptap/extension-text-style'
import { Underline } from '@tiptap/extension-underline'
import { Image } from '@tiptap/extension-image'
import { Placeholder } from '@tiptap/extension-placeholder'
import { useMessage } from 'naive-ui'
import ArVBox from '@/components/ui/ArVBox.vue'
import EditorPaper from '@/components/widgets/create/EditorPaper.vue'
import EditorToolbar from '@/components/widgets/create/EditorToolbar.vue'
import EditorCoverArea from '@/components/widgets/create/EditorCoverArea.vue'
import EditorTitleArea from '@/components/widgets/create/EditorTitleArea.vue'
import { usePostEditor } from '@/components/widgets/create/usePostEditor'
import { useFileImporter } from '@/components/widgets/create/useFileImporter'

const route = useRoute()
const router = useRouter()
const message = useMessage()

const editor = usePostEditor()
const fileImporter = useFileImporter()

const isEditing = computed(() => !!route.query.postId)
const showCover = ref(false)

/** TipTap 编辑器实例（@tiptap/vue-3 useEditor 返回的是 Ref<Editor>，直接使用） */
const tipTapEditor = useEditor({
  content: '',
  extensions: [
    StarterKit.configure({
      heading: { levels: [1, 2, 3, 4] },
      bulletList: { keepMarks: true, keepAttributes: false },
      orderedList: { keepMarks: true, keepAttributes: false }
    }),
    TextStyle,
    TextAlign.configure({ types: ['heading', 'paragraph'] }),
    Underline,
    Image.configure({ inline: false }),
    Placeholder.configure({
      placeholder: 'Okay, let us begin our story'
    })
  ],
  editorProps: {
    attributes: {
      class: 'prose-editor'
    }
  },
  onUpdate: ({ editor: ed }) => {
    editor.content.value = JSON.stringify(ed.getJSON())
  }
})

const hasActiveEditor = computed(() => !!tipTapEditor.value)

onMounted(async () => {
  const postId = route.query.postId as string | undefined
  if (postId) {
    await editor.loadPost(postId)
    if (editor.coverUrl.value) showCover.value = true
    // 加载帖子后设置编辑器内容
    setEditorContent(editor.content.value)
  } else {
    editor.resetForNew()
  }
})

function setEditorContent(val: string) {
  const ed = tipTapEditor.value
  if (!ed || !val) return
  try {
    const json = JSON.parse(val)
    ed.commands.setContent(json)
  } catch {
    ed.commands.setContent(val)
  }
}

function handleCancel() {
  router.push('/create')
}

async function handleSaveDraft() {
  await editor.save()
}

async function handlePublish() {
  const ok = await editor.save()
  if (ok) {
    router.push('/create')
  }
}

function toggleCover() {
  showCover.value = !showCover.value
}

/** 执行工具栏格式化命令 */
function execCommand(cmd: string) {
  const ed = tipTapEditor.value
  if (!ed) return
  const chain = ed.chain().focus()
  const cmdMap: Record<string, () => void> = {
    toggleBold: () => chain.toggleBold().run(),
    toggleItalic: () => chain.toggleItalic().run(),
    toggleUnderline: () => chain.toggleUnderline().run(),
    toggleStrike: () => chain.toggleStrike().run(),
    toggleCode: () => chain.toggleCode().run(),
    toggleBlockquote: () => chain.toggleBlockquote().run(),
    toggleBulletList: () => chain.toggleBulletList().run(),
    toggleOrderedList: () => chain.toggleOrderedList().run(),
    setTextAlignLeft: () => chain.setTextAlign('left').run(),
    setTextAlignCenter: () => chain.setTextAlign('center').run(),
    setTextAlignRight: () => chain.setTextAlign('right').run(),
    toggleHeading1: () => chain.toggleHeading({ level: 1 }).run(),
    toggleHeading2: () => chain.toggleHeading({ level: 2 }).run(),
    toggleHeading3: () => chain.toggleHeading({ level: 3 }).run(),
    toggleHeading4: () => chain.toggleHeading({ level: 4 }).run(),
    undo: () => chain.undo().run(),
    redo: () => chain.redo().run(),
    setColor: () => chain.setColor('#b83a2a').run()
  }
  cmdMap[cmd]?.()
}

/** 导入文件 */
async function handleImportFile() {
  const result = await fileImporter.pickAndRead()
  if (!result) {
    if (fileImporter.importError.value) {
      message.error(fileImporter.importError.value)
    }
    return
  }

  const ed = tipTapEditor.value
  if (ed) {
    const { marked } = await import('marked')
    const html = marked.parse(result.text) as string
    ed.commands.setContent(html)
    message.success('文件已导入')
  }
}
</script>

<template>
  <ArVBox style="min-height: 100vh; background: var(--bg-gradient)">
    <EditorPaper>
      <EditorToolbar
        :has-active-editor="hasActiveEditor"
        :saving="editor.saving.value"
        :is-edit="isEditing"
        :exec-command="execCommand"
        @cancel="handleCancel"
        @toggle-cover="toggleCover"
        @import-file="handleImportFile"
        @save-draft="handleSaveDraft"
        @publish="handlePublish"
      />

      <EditorCoverArea
        v-if="showCover"
        :title="editor.title.value"
        :introduction="''"
        :paragraphs="[]"
        :tags="editor.tags.value"
        @update:cover-url="editor.coverUrl.value = $event"
      />

      <EditorTitleArea
        :title="editor.title.value"
        :subtitles="editor.subtitles.value"
        @update:title="editor.title.value = $event"
        @update:subtitle="(idx: number, val: string) => (editor.subtitles.value[idx] = val)"
        @add-subtitle="editor.subtitles.value.push('')"
        @remove-subtitle="(idx: number) => editor.subtitles.value.splice(idx, 1)"
      />

      <div>
        <EditorContent :editor="tipTapEditor" />
      </div>
    </EditorPaper>
  </ArVBox>
</template>
