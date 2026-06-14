<script setup lang="ts">
/**
 * EditorImageUploader — 图片卡片编辑区
 *
 * 上传图片 → 直接预览。支持点击上传和拖拽上传。
 */
import { ref } from 'vue'
import ArButton from '@/components/ui/ArButton.vue'

defineProps<{
  mediaUrl: string
  caption: string
}>()

const emit = defineEmits<{
  'update:mediaUrl': [url: string]
  'update:caption': [value: string]
}>()

const isDragOver = ref(false)

function handleFileSelected(file: File) {
  if (!file.type.startsWith('image/')) return
  const url = URL.createObjectURL(file)
  emit('update:mediaUrl', url)
  // TODO: 实际场景中上传到 OSS，这里先做本地 blob
}

function handleFileInput(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (file) handleFileSelected(file)
  input.value = ''
}

function handleDrop(e: DragEvent) {
  isDragOver.value = false
  const file = e.dataTransfer?.files[0]
  if (file) handleFileSelected(file)
}
</script>

<template>
  <div class="image-editor">
    <!-- 已有图片 → 预览 -->
    <div v-if="mediaUrl" class="image-preview">
      <img :src="mediaUrl" :alt="caption || '图片'" />
      <div class="image-actions">
        <ArButton size="sm" type="secondary" @click="emit('update:mediaUrl', '')">
          更换图片
        </ArButton>
      </div>
      <input
        :value="caption"
        class="caption-input"
        placeholder="图片说明（可选）"
        maxlength="256"
        @input="emit('update:caption', ($event.target as HTMLInputElement).value)"
      />
    </div>

    <!-- 无图片 → 上传区域 -->
    <div
      v-else
      class="upload-zone"
      :class="{ 'drag-over': isDragOver }"
      @dragover.prevent="isDragOver = true"
      @dragleave="isDragOver = false"
      @drop.prevent="handleDrop"
      @click="$refs.fileInput?.click()"
    >
      <div class="upload-hint">
        <p>点击或拖拽上传图片</p>
        <p class="upload-sub">支持 JPG / PNG / WebP</p>
      </div>
      <input
        ref="fileInput"
        type="file"
        accept="image/*"
        class="file-input-hidden"
        @change="handleFileInput"
      />
    </div>
  </div>
</template>

<style scoped>
.image-editor {
  padding: 12px;
  min-height: 100px;
}

.image-preview {
  text-align: center;
}

.image-preview img {
  max-width: 100%;
  max-height: 400px;
  border-radius: var(--radius-md);
  display: block;
  margin: 0 auto;
}

.image-actions {
  margin-top: 8px;
}

.caption-input {
  width: 100%;
  margin-top: 8px;
  padding: 6px 10px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--text-primary);
  font-size: 13px;
  text-align: center;
  outline: none;
}

.upload-zone {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 120px;
  border: 2px dashed var(--border-color);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.upload-zone:hover,
.upload-zone.drag-over {
  border-color: var(--primary-color);
  background: var(--primary-light-color);
}

.upload-hint {
  text-align: center;
  color: var(--text-tertiary);
}

.upload-sub {
  font-size: 12px;
  margin-top: 4px;
}

.file-input-hidden {
  display: none;
}
</style>
