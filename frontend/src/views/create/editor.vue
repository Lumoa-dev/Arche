<template>
  <EditorLayout>
    <template #sidebar>
      <EditorSidebar
        :posts="manager.posts.value"
        :active-post-id="editor.editingPost.value?.id ?? null"
        @select="editor.switchPost"
        @back="goBack"
      />
    </template>
    <template #topbar>
      <EditorTopBar
        :status="editor.editingPost.value?.status ?? null"
        :is-new="editor.isNew.value"
        :tags="editor.tags.value"
        :access="editor.access.value"
        @update:tags="editor.tags.value = $event"
        @update:access="editor.access.value = $event"
        @save="handleSave"
        @cancel="goBack"
      />
    </template>
    <template #editor>
      <PostEditor
        ref="editorRef"
        :post="editor.isNew.value ? null : editor.editingPost.value"
        :cover-url="editor.coverUrl.value"
        :loading="editor.saving.value"
        hide-footer
        @cancel="goBack"
      />
    </template>
    <template #sidebar-inner>
      <CoverUploader
        v-model:cover-url="editor.coverUrl.value"
        @cover-file="editor.handleCoverFile"
      />
      <AssetSidebar
        :staged-files="editor.stagedFiles.value"
        @insert="handleInsertRef"
        @upload="editor.stageFiles"
      />
    </template>
  </EditorLayout>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useMessage } from 'naive-ui'
import { marked } from 'marked'
import EditorLayout from '@/components/widgets/blog/EditorLayout.vue'
import EditorSidebar from '@/components/widgets/blog/EditorSidebar.vue'
import EditorTopBar from '@/components/widgets/blog/EditorTopBar.vue'
import PostEditor from '@/components/widgets/blog/PostEditor.vue'
import CoverUploader from '@/components/widgets/blog/CoverUploader.vue'
import AssetSidebar from '@/components/widgets/blog/AssetSidebar.vue'
import { usePostManager } from '@/components/logic/usePostManager'
import { usePostEditor } from '@/components/logic/usePostEditor'
import { getCoverGradient } from '@/lib/utils/cover'
import { getPostByIdApi } from '@/components/logic/api'

const route = useRoute()
const router = useRouter()
const message = useMessage()
const editorRef = ref<InstanceType<typeof PostEditor> | null>(null)

const manager = usePostManager()
const editor = usePostEditor()

function goBack() {
  router.push('/create')
}

function handleInsertRef(refStr: string) {
  if (editorRef.value) {
    editorRef.value.content += refStr
  }
}

async function handleSave() {
  if (!editorRef.value) return
  const title = editorRef.value.title.trim()
  const content = editorRef.value.content.trim()
  if (!title || !content) {
    message.warning('标题和内容不能为空')
    return
  }
  await editor.save(title, content, manager.refreshPosts)
  message.success('保存成功')
}

// 从创作列表页导航过来时，检查 sessionStorage 中是否有待编辑的帖子
onMounted(async () => {
  await manager.fetchData()
  const editId = sessionStorage.getItem('editPostId')
  if (editId) {
    sessionStorage.removeItem('editPostId')
    try {
      const post = await getPostByIdApi(editId)
      editor.openEdit(post)
    } catch {
      // 加载帖子失败，新建一篇
      editor.openNew()
    }
  } else {
    editor.openNew()
  }
})

// 编辑器挂载后，若有导入的文件内容则填充
watch(editorRef, (editorComponent) => {
  if (editorComponent && editor.pendingImport.value) {
    const data = editor.pendingImport.value as any
    editorComponent.title = data.title || ''
    const rawContent = data.content || ''
    editorComponent.content = rawContent ? (marked.parse(rawContent, { gfm: true }) as string) : ''
    if (data.cover_url) {
      editor.coverUrl.value = data.cover_url
    } else {
      editor.coverUrl.value = getCoverGradient({ title: data.title, tags: data.tags })
    }
    editor.pendingImport.value = null
  }
})
</script>
