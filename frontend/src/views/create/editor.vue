<script setup lang="ts">
/**
 * editor.vue — 段落编辑器主页面
 *
 * 全页卡片式编辑，所有操作集中在工具栏。
 * 结构：工具栏 → 封面预览 → 标题区 → 引言 → 段落卡片
 */
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import ArVBox from '@/components/ui/ArVBox.vue'
import ArSortable from '@/components/ui/ArSortable.vue'
import EditorToolbar from '@/components/widgets/create/EditorToolbar.vue'
import EditorBody from '@/components/widgets/create/EditorBody.vue'
import EditorCoverArea from '@/components/widgets/create/EditorCoverArea.vue'
import EditorTitleArea from '@/components/widgets/create/EditorTitleArea.vue'
import EditorIntroductionCard from '@/components/widgets/create/EditorIntroductionCard.vue'
import EditorParagraphCard from '@/components/widgets/create/EditorParagraphCard.vue'
import {
  useParagraphEditor,
  type ParagraphType
} from '@/components/widgets/create/useParagraphEditor'
import { useFileImporter } from '@/components/widgets/create/useFileImporter'
import PipelineProgress from '@/components/widgets/create/PipelineProgress.vue'
import type { Editor } from '@tiptap/vue-3'
import { useMessage } from 'naive-ui'
import { $notification } from '@/lib/utils/message'

const route = useRoute()
const router = useRouter()

const editor = useParagraphEditor()
const fileImporter = useFileImporter()
const message = useMessage()

/** 各段落 uid → TipTap editor 实例映射（供工具栏联动） */
const editorMap = ref<Record<string, Editor>>({})
const hasActiveEditor = computed(() => Object.keys(editorMap.value).length > 0)
/** 当前聚焦的编辑器实例 */
const activeEditor = ref<Editor | null>(null)

const isEditing = computed(() => !!route.query.postId)

/** 封面是否显示 */
const showCover = ref(false)

/** 流水线弹窗可见 */
const pipelineDialogVisible = ref(false)
const importPipelineDialogVisible = ref(false)

/** 用户是否隐藏了弹窗（后台运行模式） */
const savePipelineHidden = ref(false)
const importPipelineHidden = ref(false)

/** 监听流水线进度：手动编辑保存时 */
const _saveProgressWatcher = watch(
  () => editor.pipelineProgress.value,
  (p) => {
    if (!p) return
    if (p.currentStage !== null) {
      pipelineDialogVisible.value = true
    }
    // 隐藏模式下完成 → 通知
    if (savePipelineHidden.value && p.overallProgress === 100 && !p.error) {
      savePipelineHidden.value = false
      $notification.success({
        title: '保存完成',
        content: `段落已标准化，共 ${p.stages.find((s) => s.stage === 'parse')?.message || ''} 个段落`,
        duration: 3000
      })
    }
    // 隐藏模式下出错 → 通知
    if (savePipelineHidden.value && p.error) {
      savePipelineHidden.value = false
      $notification.error({
        title: '保存失败',
        content: p.error,
        duration: 5000
      })
    }
  }
)

// 监听导入流水线进度
const _importProgressWatcher = watch(
  () => fileImporter.importProgress.value,
  (p) => {
    if (!p) return
    if (p.currentStage !== null) {
      importPipelineDialogVisible.value = true
    }
    // 隐藏模式下完成 → 通知
    if (importPipelineHidden.value && p.overallProgress === 100 && !p.error) {
      importPipelineHidden.value = false
      $notification.success({
        title: '导入完成',
        content: `文件已解析，共 ${p.stages.find((s) => s.stage === 'parse')?.message || ''}`,
        duration: 3000
      })
    }
    // 隐藏模式下出错 → 通知
    if (importPipelineHidden.value && p.error) {
      importPipelineHidden.value = false
      $notification.error({
        title: '导入失败',
        content: p.error,
        duration: 5000
      })
    }
  }
)

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

function handleSavePipelineHide() {
  savePipelineHidden.value = true
  pipelineDialogVisible.value = false
}

function handleImportPipelineHide() {
  importPipelineHidden.value = true
  importPipelineDialogVisible.value = false
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

/** 处理从工具栏拖拽插入的段落 */
function handleExternalDrop(payload: { element: string; newIndex: number }) {
  const raw = payload.element
  if (typeof raw !== 'string' || !raw.startsWith('paragraph:')) return
  const type = raw.replace('paragraph:', '') as ParagraphType
  editor.addParagraph(type, payload.newIndex)
}

/** 导入文件 */
async function handleImportFile() {
  const result = await fileImporter.pickAndParse()
  if (!result) {
    if (fileImporter.importError.value) {
      message.error(fileImporter.importError.value)
    }
    return
  }

  // 填充编辑器
  editor.title.value = result.title || editor.title.value
  editor.subtitles.value = [...editor.subtitles.value, ...result.subtitles.slice(0, 3)]
  if (result.introduction) {
    editor.introduction.value = result.introduction
  }
  if (result.paragraphs.length > 0) {
    editor.paragraphs.value = fileImporter.toEditorParagraphs(result)
  }

  message.success(`已导入 ${result.paragraphs.length} 个段落`)
}
</script>

<template>
  <ArVBox style="min-height: 100vh; background: var(--bg-gradient)">
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
        @import-file="handleImportFile"
        @save-draft="handleSaveDraft"
        @publish="handlePublish"
      />
      <!-- 封面 -->
      <EditorCoverArea
        v-if="showCover"
        :title="editor.title.value"
        :introduction="editor.introduction.value"
        :paragraphs="editor.paragraphs.value"
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

      <!-- 段落卡片列表（ArSortable 拖拽排序） -->
      <ArSortable
        v-model="editor.paragraphs.value"
        axis="y"
        handle=".drag-rail"
        :animation="150"
        ghost="line"
        item-key="uid"
        @add="handleExternalDrop"
      >
        <template #item="{ element: para, index: idx }">
          <EditorParagraphCard
            :paragraph="para"
            :can-move-up="idx > 0"
            :can-move-down="idx < editor.paragraphs.value.length - 1"
            @update:type="(uid: string, type: any) => editor.setParagraphType(uid, type)"
            @move-up="(uid: string) => editor.moveParagraphUp(uid)"
            @move-down="(uid: string) => editor.moveParagraphDown(uid)"
            @delete="(uid: string) => editor.removeParagraph(uid)"
            @update:content="
              (uid: string, content: string) => editor.updateParagraphContent(uid, content)
            "
            @update:media-url="
              (uid: string, url: string) => editor.updateParagraphMediaUrl(uid, url)
            "
            @update:caption="
              (uid: string, caption: string) => editor.updateParagraphCaption(uid, caption)
            "
            @ready="handleParagraphReady"
            @focus="handleEditorFocus"
          />
        </template>
      </ArSortable>
    </EditorBody>
  </ArVBox>

  <!-- 保存流水线进度弹窗 -->
  <PipelineProgress
    :visible="pipelineDialogVisible"
    :progress="editor.pipelineProgress.value"
    title="正在保存..."
    @close="pipelineDialogVisible = false"
    @hide="handleSavePipelineHide"
  />

  <!-- 导入流水线进度弹窗 -->
  <PipelineProgress
    :visible="importPipelineDialogVisible"
    :progress="fileImporter.importProgress.value"
    title="正在导入文件..."
    @close="importPipelineDialogVisible = false"
    @hide="handleImportPipelineHide"
  />
</template>
