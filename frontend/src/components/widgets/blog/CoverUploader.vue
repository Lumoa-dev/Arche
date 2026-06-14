<script setup lang="ts">
import { ref } from 'vue'

defineProps<{
  coverUrl: string
}>()

const emit = defineEmits<{
  'update:coverUrl': [url: string]
  coverFile: [file: File] // 当用户选择本地文件时，传出原始 File 供保存时上传
}>()

// ── 状态 ──
const isDragOver = ref(false)

// ── 点击选择本地文件 ──
function handleClick() {
  const input = document.createElement('input')
  input.type = 'file'
  input.accept = 'image/*'
  input.onchange = () => {
    const file = input.files?.[0]
    if (!file) return
    if (!file.type.startsWith('image/')) return
    if (file.size > 10 * 1024 * 1024) return

    // 本地 blob URL 预览
    const blobUrl = URL.createObjectURL(file)
    emit('update:coverUrl', blobUrl)
    emit('coverFile', file)
  }
  input.click()
}

// ── 文件拖拽 ──
function handleDragOver(e: DragEvent) {
  e.preventDefault()
  e.stopPropagation()
  isDragOver.value = true
}

function handleDragLeave(e: DragEvent) {
  e.preventDefault()
  e.stopPropagation()
  isDragOver.value = false
}

function handleDrop(e: DragEvent) {
  e.preventDefault()
  e.stopPropagation()
  isDragOver.value = false

  // 1. 先检查是否有 URL 拖入（从 AssetSidebar 拖拽）
  const url = e.dataTransfer?.getData('text/plain')
  if (url && (url.startsWith('blob:') || url.startsWith('/api/oss/'))) {
    emit('update:coverUrl', url)
    return
  }

  // 2. 否则尝试文件拖入
  const file = e.dataTransfer?.files?.[0]
  if (file && file.type.startsWith('image/')) {
    const blobUrl = URL.createObjectURL(file)
    emit('update:coverUrl', blobUrl)
    emit('coverFile', file)
  }
}

// ── 删除封面 ──
function handleDelete(e: MouseEvent) {
  e.stopPropagation()
  emit('update:coverUrl', '')
}
</script>

<template>
  <div class="cover-uploader">
    <!-- 有封面 → 预览模式 -->
    <div v-if="coverUrl" class="cover-preview" @click="handleClick">
      <img :src="coverUrl" alt="封面预览" class="cover-image" />
      <div class="cover-overlay">
        <span class="overlay-text">更换封面</span>
      </div>
      <button class="cover-delete-btn" aria-label="删除封面" @click.stop="handleDelete">
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          class="delete-icon"
        >
          <line x1="18" y1="6" x2="6" y2="18" />
          <line x1="6" y1="6" x2="18" y2="18" />
        </svg>
      </button>
    </div>

    <!-- 无封面 → 上传区域（同时接受本地文件 + 素材拖入） -->
    <div
      v-else
      :class="['cover-upload-area', { 'is-dragover': isDragOver }]"
      @click="handleClick"
      @dragover="handleDragOver"
      @dragleave="handleDragLeave"
      @drop="handleDrop"
    >
      <svg
        class="upload-area-icon"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="1.5"
      >
        <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
        <circle cx="8.5" cy="8.5" r="1.5" />
        <polyline points="21 15 16 10 5 21" />
      </svg>
      <div class="upload-area-text">
        <span class="upload-area-title">点击上传封面</span>
        <span class="upload-area-hint">或将素材拖到这里</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.cover-uploader {
  width: 100%;
  max-width: 100%;
  border-radius: var(--radius-md);
  overflow: hidden;
  font-family: var(--font-sans);
}

/* ── 上传区域 ── */
.cover-upload-area {
  position: relative;
  width: 100%;
  aspect-ratio: 16 / 9;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-sm);
  border: 2px dashed var(--border-color);
  border-radius: var(--radius-md);
  background: var(--surface-color);
  cursor: pointer;
  transition:
    border-color var(--transition-normal),
    background-color var(--transition-normal);
}

.cover-upload-area:hover {
  border-color: var(--primary-color);
  background: var(--primary-light-color);
}

.cover-upload-area.is-dragover {
  border-color: var(--primary-color);
  background: var(--primary-light-color);
  box-shadow: 0 0 0 3px var(--primary-light-color);
}

.upload-area-icon {
  width: 36px;
  height: 36px;
  color: var(--text-tertiary);
  transition: color var(--transition-fast);
}

.cover-upload-area:hover .upload-area-icon {
  color: var(--primary-color);
}

.upload-area-text {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}

.upload-area-title {
  font-size: 14px;
  font-weight: var(--font-weight-medium);
  color: var(--text-secondary);
  transition: color var(--transition-fast);
}

.cover-upload-area:hover .upload-area-title {
  color: var(--primary-color);
}

.upload-area-hint {
  font-size: 11px;
  color: var(--text-tertiary);
}

/* ── 预览模式 ── */
.cover-preview {
  position: relative;
  width: 100%;
  aspect-ratio: 16 / 9;
  border-radius: var(--radius-md);
  overflow: hidden;
  cursor: pointer;
  background: var(--surface-inset-color);
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
  transition: background-color var(--transition-normal);
}

.cover-preview:hover .cover-overlay {
  background: rgba(0, 0, 0, 0.45);
}

.overlay-text {
  font-size: 13px;
  font-weight: var(--font-weight-medium);
  color: #fff;
  opacity: 0;
  transition: opacity var(--transition-normal);
}

.cover-preview:hover .overlay-text {
  opacity: 1;
}

/* ── 删除按钮 ── */
.cover-delete-btn {
  position: absolute;
  top: var(--spacing-sm);
  right: var(--spacing-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  padding: 0;
  border: none;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.55);
  color: #fff;
  cursor: pointer;
  opacity: 0;
  transition:
    opacity var(--transition-fast),
    background-color var(--transition-fast);
  z-index: 2;
}

.cover-preview:hover .cover-delete-btn {
  opacity: 1;
}

.cover-delete-btn:hover {
  background: var(--error-color);
}

.delete-icon {
  width: 14px;
  height: 14px;
}
</style>
