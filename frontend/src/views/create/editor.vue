<script setup lang="ts">
/**
 * editor.vue — 段落编辑器主页面
 *
 * 全页卡片式编辑，所有操作集中在工具栏。
 * 结构：工具栏 → 封面预览 → 标题区 → 引言 → 段落卡片
 */
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import ArVBox from '@/components/ui/ArVBox.vue'
import EditorToolbar from '@/components/widgets/create/EditorToolbar.vue'
import EditorBody from '@/components/widgets/create/EditorBody.vue'
import EditorCoverArea from '@/components/widgets/create/EditorCoverArea.vue'
import EditorTitleArea from '@/components/widgets/create/EditorTitleArea.vue'
import EditorIntroductionCard from '@/components/widgets/create/EditorIntroductionCard.vue'
import EditorParagraphCard from '@/components/widgets/create/EditorParagraphCard.vue'
import { useParagraphEditor } from '@/components/logic/useParagraphEditor'
import type { Editor } from '@tiptap/vue-3'

const route = useRoute()
const router = useRouter()

const editor = useParagraphEditor()

/** 各段落 uid → TipTap editor 实例映射（供工具栏联动） */
const editorMap = ref<Record<string, Editor>>({})
const hasActiveEditor = computed(() => Object.keys(editorMap.value).length > 0)
/** 当前聚焦的编辑器实例 */
const activeEditor = ref<Editor | null>(null)

const isEditing = computed(() => !!route.query.postId)

/** 封面是否显示 */
const showCover = ref(false)

onMounted(async () => {
  const postId = route.query.postId as string | undefined
  if (postId) {
    await editor.loadPost(postId)
    // 编辑已有帖子时自动打开封面
    if (editor.coverUrl.value) showCover.value = true
  } else {
    editor.resetForNew()
  }
})

function handleCancel() {
  router.push('/create')
}

async function handleSaveDraft() {
  // 存草稿 = 保存但标记为 draft 状态，暂用普通保存
  await editor.save()
}

async function handlePublish() {
  const ok = await editor.save()
  if (ok) {
    router.push('/create')
  }
}

function handleParagraphReady(uid: string, ed: Editor) {
  editorMap.value[uid] = ed
}

function handleEditorFocus(uid: string, ed: Editor) {
  activeEditor.value = ed
}

/**
 * 执行工具栏格式化命令
 * 直接调用当前聚焦编辑器对应的 TipTap 命令
 */
function execCommand(cmd: string) {
  const ed = activeEditor.value
  if (!ed) return
  const chain = ed.chain().focus()
  // 常用排版命令映射
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
    setColor: () => {
      // 文字颜色：弹出取色器，暂用默认红色
      chain.setColor('#b83a2a').run()
    }
  }
  cmdMap[cmd]?.()
}

function toggleCover() {
  showCover.value = !showCover.value
}
</script>

<template>
  <ArVBox style="height: 100vh; background: var(--bg-gradient)">
    <!-- 编辑区主体（可滚动+拖放），工具栏移入纸面顶部 -->
    <EditorBody @drop-paragraph="(type: any) => editor.addParagraph(type)">
      <!-- 工具栏 — 位于纸面顶部，随纸面滚动 -->
      <EditorToolbar
        :has-active-editor="hasActiveEditor"
        :saving="editor.saving.value"
        :is-edit="isEditing"
        :exec-command="execCommand"
        @cancel="handleCancel"
        @insert="(type: any) => editor.addParagraph(type)"
        @insert-separator="() => editor.addParagraph('separator')"
        @toggle-cover="toggleCover"
        @save-draft="handleSaveDraft"
        @publish="handlePublish"
      />
      <!-- 封面 -->
      <EditorCoverArea
        v-if="showCover"
        :title="editor.title.value"
        :content="editor.paragraphs.value[0]?.content || ''"
        :tags="editor.tags.value"
        @update:cover-url="editor.coverUrl.value = $event"
      />

      <!-- 标题区域 -->
      <EditorTitleArea
        :title="editor.title.value"
        :subtitles="editor.subtitles.value"
        @update:title="editor.title.value = $event"
        @update:subtitle="(idx: number, val: string) => editor.updateSubtitle(idx, val)"
        @add-subtitle="editor.addSubtitle()"
        @remove-subtitle="(idx: number) => editor.removeSubtitle(idx)"
      />

      <!-- 引言编辑区 -->
      <EditorIntroductionCard
        :model-value="editor.introduction.value"
        @update:model-value="editor.updateIntroduction($event)"
      />

      <!-- 段落卡片列表 -->
      <EditorParagraphCard
        v-for="(para, idx) in editor.paragraphs.value"
        :key="para.uid"
        :paragraph="para"
        :can-move-up="idx > 0"
        :can-move-down="idx < editor.paragraphs.value.length - 1"
        @update:type="(uid: string, type: any) => editor.setParagraphType(uid, type)"
        @move-up="(uid: string) => editor.moveParagraphUp(uid)"
        @move-down="(uid: string) => editor.moveParagraphDown(uid)"
        @delete="(uid: string) => editor.removeParagraph(uid)"
        @drop-on="(draggedUid: string, targetUid: string) => editor.moveParagraphTo(draggedUid, targetUid)"
        @update:content="
          (uid: string, content: string) => editor.updateParagraphContent(uid, content)
        "
        @update:media-url="(uid: string, url: string) => editor.updateParagraphMediaUrl(uid, url)"
        @update:caption="
          (uid: string, caption: string) => editor.updateParagraphCaption(uid, caption)
        "
        @ready="handleParagraphReady"
        @focus="handleEditorFocus"
      />
    </EditorBody>
  </ArVBox>
</template>
