<script setup lang="ts">
/**
 * EditorVideoUrlInput — 视频卡片编辑区
 *
 * 输入 URL → 即时解析并嵌入预览。
 * 支持平台：YouTube / Bilibili / Vimeo
 */
import { ref, computed } from 'vue'
import ArInput from '@/components/ui/ArInput.vue'

const props = defineProps<{
  mediaUrl: string
}>()

const emit = defineEmits<{
  'update:mediaUrl': [url: string]
}>()

const urlInput = ref(props.mediaUrl || '')

/** 解析视频平台并生成 embed URL */
const embedUrl = computed(() => {
  const url = urlInput.value.trim()
  if (!url) return null

  // YouTube
  const ytMatch = url.match(
    /(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})/
  )
  if (ytMatch) return `https://www.youtube.com/embed/${ytMatch[1]}`

  // Bilibili
  const bvMatch = url.match(/bilibili\.com\/video\/(BV[a-zA-Z0-9]+)/)
  if (bvMatch) return `https://player.bilibili.com/player.html?bvid=${bvMatch[1]}`

  // Vimeo
  const vimeoMatch = url.match(/vimeo\.com\/(\d+)/)
  if (vimeoMatch) return `https://player.vimeo.com/video/${vimeoMatch[1]}`

  return null
})

const platformLabel = computed(() => {
  if (!urlInput.value.trim()) return ''
  if (embedUrl.value) return '预览加载中…'
  return '⚠️ 暂不支持此平台，仅支持 YouTube / Bilibili / Vimeo'
})

function handleUrlUpdate(val: string) {
  urlInput.value = val
  emit('update:mediaUrl', val)
}
</script>

<template>
  <div class="video-editor">
    <div class="url-input-row">
      <ArInput
        :model-value="urlInput"
        placeholder="粘贴视频链接（YouTube / Bilibili / Vimeo）"
        style="flex: 1"
        @update:model-value="handleUrlUpdate"
      />
    </div>

    <p v-if="platformLabel && !embedUrl" class="platform-hint error">
      {{ platformLabel }}
    </p>

    <!-- 视频预览 -->
    <div v-if="embedUrl" class="video-preview">
      <iframe :src="embedUrl" frameborder="0" allowfullscreen loading="lazy" />
    </div>
  </div>
</template>

<style scoped>
.video-editor {
  padding: 12px;
}

.url-input-row {
  display: flex;
  gap: 8px;
  margin-bottom: 8px;
}

.platform-hint {
  font-size: 12px;
  margin-bottom: 8px;
}

.platform-hint.error {
  color: var(--error-color);
}

.video-preview {
  position: relative;
  width: 100%;
  aspect-ratio: 16 / 9;
  border-radius: var(--radius-md);
  overflow: hidden;
  background: #000;
  margin-top: 8px;
}

.video-preview iframe {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  border: none;
}
</style>
