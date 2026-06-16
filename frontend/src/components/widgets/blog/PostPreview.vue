<script setup lang="ts">
import { computed, ref, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { useEditor, EditorContent } from '@tiptap/vue-3'
import { StarterKit } from '@tiptap/starter-kit'
import { TextAlign } from '@tiptap/extension-text-align'
import { TextStyle } from '@tiptap/extension-text-style'
import { Underline } from '@tiptap/extension-underline'
import { Image } from '@tiptap/extension-image'
import type { BlogPost } from '@/lib/services/api'

const props = defineProps<{
  post: BlogPost
  postId: string
}>()

const router = useRouter()
const subtitles = computed(() => props.post?.subtitles || [])
const introduction = computed(() => props.post?.introduction || '')

/** TipTap 只读编辑器（预览 content） */
const contentEditor = ref<ReturnType<typeof useEditor> | null>(null)

function goBack() {
  router.push(`/create/editor?postId=${props.postId}`)
}

onMounted(() => {
  if (props.post?.content) {
    try {
      const json = JSON.parse(props.post.content)
      contentEditor.value = useEditor({
        content: json,
        editable: false,
        extensions: [
          StarterKit.configure({ heading: { levels: [1, 2, 3, 4] } }),
          TextStyle,
          TextAlign.configure({ types: ['heading', 'paragraph'] }),
          Underline,
          Image.configure({ inline: false })
        ],
        editorProps: {
          attributes: { class: 'preview-content-editor' }
        }
      })
    } catch {
      contentEditor.value = null
    }
  }
})

onBeforeUnmount(() => {
  contentEditor.value?.destroy()
})
</script>

<template>
  <div>
    <!-- 返回编辑 -->
    <div style="margin-bottom: var(--spacing-lg)">
      <button class="back-btn" @click="goBack">← 返回编辑</button>
    </div>

    <!-- 标题 -->
    <h1 class="preview-title">{{ post.title }}</h1>

    <!-- 副标题 -->
    <div v-if="subtitles.length > 0" class="preview-subtitles">
      <p v-for="(sub, idx) in subtitles" :key="idx" class="preview-subtitle">
        {{ sub }}
      </p>
    </div>

    <!-- 引言 -->
    <!-- eslint-disable-next-line vue/no-v-html -->
    <div v-if="introduction" class="preview-introduction" v-html="introduction" />

    <!-- 正文：TipTap 渲染 -->
    <div v-if="contentEditor" class="preview-content-wrapper">
      <EditorContent :editor="contentEditor" />
    </div>
  </div>
</template>

<style scoped>
.back-btn {
  padding: 6px 16px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  background: var(--surface-color);
  color: var(--text-secondary);
  font-size: 13px;
  font-family: var(--font-sans);
  cursor: pointer;
  transition: all var(--transition-fast);
}
.back-btn:hover {
  border-color: var(--primary-color);
  color: var(--primary-color);
}
.preview-title {
  font-size: 2em;
  font-weight: var(--font-weight-bold);
  line-height: 1.3;
  margin: 0 0 var(--spacing-sm);
  color: var(--text-primary);
  font-family: var(--font-serif);
}
.preview-subtitles {
  margin-bottom: var(--spacing-lg);
}
.preview-subtitle {
  font-size: 1.1em;
  color: var(--text-tertiary);
  margin: 0.2em 0;
  line-height: 1.5;
  font-family: var(--font-serif);
}
.preview-introduction {
  margin: var(--spacing-md) 0 var(--spacing-lg);
  padding: var(--spacing-md);
  background: var(--surface-hover-color);
  border-radius: var(--radius-sm);
  border-left: 3px solid var(--primary-color);
  font-family: var(--font-serif);
  font-size: 1.05em;
  line-height: 1.7;
  color: var(--text-secondary);
}
.preview-content-wrapper {
  font-family: var(--font-serif);
  line-height: 1.8;
  color: var(--text-primary);
  margin-top: var(--spacing-lg);
}
.preview-content-wrapper :deep(.ProseMirror) {
  outline: none;
}
.preview-content-wrapper :deep(.ProseMirror p) {
  margin: 0.6em 0;
}
.preview-content-wrapper :deep(.ProseMirror h2) {
  font-size: 1.5em;
  font-weight: var(--font-weight-bold);
  margin: 0.7em 0 0.3em;
}
.preview-content-wrapper :deep(.ProseMirror h3) {
  font-size: 1.25em;
  font-weight: var(--font-weight-semibold);
  margin: 0.6em 0 0.3em;
}
.preview-content-wrapper :deep(.ProseMirror img) {
  max-width: 100%;
  height: auto;
  border-radius: var(--radius-sm);
  margin: var(--spacing-md) 0;
}
</style>
