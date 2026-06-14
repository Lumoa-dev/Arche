<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getMyOssFilesApi, getOssFileUrl } from '@/components/logic/api'
import type { StagedFile } from '@/components/logic/useLocalFiles'
import type { OSSFile } from '@/components/logic/api'

const props = withDefaults(
  defineProps<{
    stagedFiles?: StagedFile[]
  }>(),
  {
    stagedFiles: () => []
  }
)

const emit = defineEmits<{
  insert: [refStr: string]
  upload: [files: File[]]
}>()

// ── 状态 ──
const ossFiles = ref<OSSFile[]>([])
const loading = ref(false)

// ── 合并展示：暂存文件优先 ──
interface DisplayFile {
  id: string
  index: number
  url: string
  name: string
  isStaged: boolean // 暂存文件可拖拽
}

const displayFiles = ref<DisplayFile[]>([])

function buildDisplayList() {
  const items: DisplayFile[] = []

  // 暂存文件
  let stagedIdx = 1
  for (const sf of props.stagedFiles) {
    items.push({
      id: sf.id,
      index: sf.index,
      url: sf.blobUrl,
      name: sf.name,
      isStaged: true
    })
    stagedIdx++
  }

  // OSS 已有文件
  for (const ofs of ossFiles.value) {
    const idx = stagedIdx++
    items.push({
      id: ofs.id,
      index: idx,
      url: getOssFileUrl(ofs.id),
      name: ofs.path || ofs.id,
      isStaged: false
    })
  }

  displayFiles.value = items
}

// ── 获取 OSS 文件列表 ──
async function fetchFiles() {
  loading.value = true
  try {
    const result = await getMyOssFilesApi({ limit: 50, offset: 0 }, { silent: true })
    ossFiles.value = result.list || []
  } catch {
    ossFiles.value = []
  } finally {
    loading.value = false
    buildDisplayList()
  }
}

// ── 监听暂存文件变化 ──
import { watch } from 'vue'
watch(() => props.stagedFiles, buildDisplayList, { deep: true })

// ── 点击插入 ──
function handleFileClick(df: DisplayFile) {
  emit('insert', `#${df.index}`)
}

// ── 拖拽开始 ──
function handleDragStart(e: DragEvent, df: DisplayFile) {
  if (!df.isStaged) return // 仅暂存文件可拖拽到封面
  e.dataTransfer?.setData('text/plain', df.url)
  e.dataTransfer?.setData('application/x-index', String(df.index))
  e.dataTransfer!.effectAllowed = 'copy'
  if (e.target instanceof HTMLElement) {
    e.target.style.opacity = '0.5'
  }
}

function handleDragEnd(e: DragEvent) {
  if (e.target instanceof HTMLElement) {
    e.target.style.opacity = '1'
  }
}

// ── 多选上传 ──
function handleUploadClick() {
  const input = document.createElement('input')
  input.type = 'file'
  input.accept = 'image/*'
  input.multiple = true
  input.onchange = () => {
    const files = input.files
    if (!files || files.length === 0) return
    // 大小过滤
    const valid: File[] = []
    for (const f of Array.from(files)) {
      if (f.size > 10 * 1024 * 1024) {
        continue // 跳过超大的，不阻塞流程
      }
      valid.push(f)
    }
    if (valid.length === 0) return
    emit('upload', valid)
  }
  input.click()
}

onMounted(fetchFiles)
</script>

<template>
  <aside class="asset-sidebar">
    <div class="sidebar-header">
      <h3 class="sidebar-title">帖子素材</h3>
    </div>

    <!-- 上传按钮 -->
    <button class="upload-btn" @click="handleUploadClick">
      <svg
        class="upload-icon"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
      >
        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
        <polyline points="17 8 12 3 7 8" />
        <line x1="12" y1="3" x2="12" y2="15" />
      </svg>
      <span>添加素材</span>
    </button>

    <!-- 加载中 -->
    <div v-if="loading" class="sidebar-status">
      <div class="loading-spinner" />
      <span>加载中...</span>
    </div>

    <!-- 空状态 -->
    <div v-else-if="displayFiles.length === 0" class="sidebar-status sidebar-empty">
      <svg
        class="empty-icon"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="1.5"
      >
        <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
        <circle cx="8.5" cy="8.5" r="1.5" />
        <polyline points="21 15 16 10 5 21" />
      </svg>
      <span>暂无素材，点击上方添加</span>
    </div>

    <!-- 文件网格 -->
    <div v-else class="file-grid">
      <button
        v-for="df in displayFiles"
        :key="df.id"
        :draggable="df.isStaged"
        class="file-item"
        :class="{ 'is-staged': df.isStaged }"
        :title="`#${df.index} - ${df.name}${df.isStaged ? ' (暂存)' : ''}`"
        @click="handleFileClick(df)"
        @dragstart="handleDragStart($event, df)"
        @dragend="handleDragEnd"
      >
        <img :src="df.url" :alt="df.name" class="file-thumb" loading="lazy" />
        <span class="file-badge">#{{ df.index }}</span>
        <span v-if="df.isStaged" class="file-staged-tag">暂存</span>
      </button>
    </div>
  </aside>
</template>

<style scoped>
.asset-sidebar {
  width: 280px;
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
  padding: var(--spacing-md);
  font-family: var(--font-sans);
  height: 100%;
  overflow-y: auto;
}

.sidebar-header {
  padding-bottom: var(--spacing-sm);
  border-bottom: 1px solid var(--border-color);
}

.sidebar-title {
  margin: 0;
  font-size: 14px;
  font-weight: var(--font-weight-semibold);
  color: var(--text-primary);
}

/* ── 上传按钮 ── */
.upload-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  width: 100%;
  padding: 8px 16px;
  background: var(--primary-color);
  color: #fff;
  border: none;
  border-radius: var(--radius-sm);
  font-family: var(--font-sans);
  font-size: 13px;
  font-weight: var(--font-weight-medium);
  cursor: pointer;
  transition:
    background-color var(--transition-fast),
    transform var(--transition-fast);
}

.upload-btn:hover {
  background: var(--primary-hover-color);
}

.upload-btn:active {
  transform: scale(0.97);
}

.upload-icon {
  width: 16px;
  height: 16px;
}

/* ── 状态 ── */
.sidebar-status {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-xl) 0;
  color: var(--text-tertiary);
  font-size: 13px;
}

.sidebar-empty .empty-icon {
  width: 32px;
  height: 32px;
  opacity: 0.5;
}

.loading-spinner {
  width: 24px;
  height: 24px;
  border: 2px solid var(--border-color);
  border-top-color: var(--primary-color);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

/* ── 文件网格 ── */
.file-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 6px;
  flex: 1;
}

.file-item {
  position: relative;
  width: 100%;
  aspect-ratio: 1;
  border-radius: var(--radius-sm);
  overflow: hidden;
  border: 1px solid var(--border-color);
  background: var(--surface-inset-color);
  cursor: pointer;
  padding: 0;
  transition:
    border-color var(--transition-fast),
    transform var(--transition-fast),
    box-shadow var(--transition-fast);
}

.file-item:hover {
  border-color: var(--primary-color);
  transform: translateY(-1px);
  box-shadow: var(--shadow-sm);
}

.file-item:active {
  transform: translateY(0);
}

.file-item.is-staged {
  border-style: dashed;
  border-color: var(--accent-color, #667eea);
}

.file-thumb {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.file-badge {
  position: absolute;
  right: 2px;
  bottom: 2px;
  padding: 1px 4px;
  font-size: 10px;
  font-weight: var(--font-weight-semibold);
  color: #fff;
  background: rgba(0, 0, 0, 0.55);
  border-radius: 3px;
  line-height: 1.3;
  pointer-events: none;
}

.file-staged-tag {
  position: absolute;
  top: 2px;
  left: 2px;
  padding: 1px 4px;
  font-size: 9px;
  font-weight: var(--font-weight-semibold);
  color: var(--accent-color, #667eea);
  background: rgba(255, 255, 255, 0.85);
  border-radius: 3px;
  line-height: 1.3;
  pointer-events: none;
}
</style>
