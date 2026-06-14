<script setup lang="ts">
/**
 * EditorCoverArea — 封面预览组件
 *
 * 显示在标题区域上方，自动根据文章内容生成封面。
 * 实时预览：正文改变时封面自动更新（防抖）。
 * 点击可替换为自定义图片。
 */
import { ref, watch, onBeforeUnmount } from 'vue'
import { generateTextCover } from '@/lib/utils/generateTextCover'
import type { BlogPost } from '@/components/logic/api'

const props = defineProps<{
  title: string
  content: string
  tags: string[]
}>()

const emit = defineEmits<{
  'update:coverUrl': [url: string]
}>()

const coverUrl = ref('')
const isCustomCover = ref(false) // true = 用户手动上传，不再自动更新

/** 是否有封面 */
const hasCover = ref(false)

// 防抖生成封面
let debounceTimer: ReturnType<typeof setTimeout> | null = null

function generateCover() {
  if (isCustomCover.value || !props.title) return

  const post = {
    id: 'preview',
    slug: '',
    title: props.title || 'Untitled',
    introduction: {} as any,
    paragraphs: props.content
      ? [{ content: props.content, type: 'text', pid: '', word_count: 0 }]
      : [],
    tags: props.tags
  } as BlogPost

  try {
    coverUrl.value = generateTextCover(post, true)
    hasCover.value = true
    emit('update:coverUrl', coverUrl.value)
  } catch {
    // canvas 可能不可用
  }
}

function scheduleGenerate() {
  if (isCustomCover.value) return
  if (debounceTimer) clearTimeout(debounceTimer)
  debounceTimer = setTimeout(generateCover, 500)
}

watch(() => props.title, scheduleGenerate)
watch(() => props.content, scheduleGenerate)
watch(() => props.tags, scheduleGenerate)

// 初始生成
scheduleGenerate()

onBeforeUnmount(() => {
  if (debounceTimer) clearTimeout(debounceTimer)
})

/** 用户点击替换封面 */
function handleReplace() {
  const input = document.createElement('input')
  input.type = 'file'
  input.accept = 'image/*'
  input.onchange = () => {
    const file = input.files?.[0]
    if (!file) return
    if (!file.type.startsWith('image/')) return
    if (file.size > 10 * 1024 * 1024) return

    const blobUrl = URL.createObjectURL(file)
    coverUrl.value = blobUrl
    isCustomCover.value = true
    hasCover.value = true
    emit('update:coverUrl', blobUrl)
  }
  input.click()
}
</script>

<template>
  <div v-if="hasCover" class="cover-area" @click="handleReplace">
    <img :src="coverUrl" alt="封面预览" class="cover-image" />
    <div class="cover-overlay">
      <span>点击替换封面</span>
    </div>
  </div>
</template>

<style scoped>
.cover-area {
  position: relative;
  width: 100%;
  border-radius: var(--radius-lg);
  overflow: hidden;
  cursor: pointer;
  margin-bottom: var(--spacing-md);
  aspect-ratio: 640 / 400;
  max-height: 320px;
}

.cover-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.cover-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0);
  color: #fff;
  font-size: 14px;
  font-family: var(--font-sans);
  transition: background var(--transition-fast);
  opacity: 0;
}

.cover-area:hover .cover-overlay {
  background: rgba(0, 0, 0, 0.4);
  opacity: 1;
}
</style>
