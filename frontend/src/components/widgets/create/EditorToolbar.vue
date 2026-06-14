<script setup lang="ts">
/**
 * EditorToolbar — 编辑器顶部工具栏
 *
 * Word/WPS 风格以图标为主，分组排列。
 * 所有操作集中在此，不再有底部栏。
 *
 * 排版图标（B/I/U/左中右对齐）用内联 SVG，因 @vicons/ionicons5 不含这些图标。
 * 通用图标（图片/视频/代码/保存/发送等）用 ionicons5。
 *
 * TODO: 工具栏 B/I/U/对齐 等与 TipTap 编辑器的联动
 * 当前：emit 操作命令，选中状态由父层 hasActiveEditor 控制
 */
import { ref } from 'vue'
import ArHBox from '@/components/ui/ArHBox.vue'
import ArButton from '@/components/ui/ArButton.vue'
import type { ParagraphType } from '@/components/logic/useParagraphEditor'
import {
  CodeSlashOutline,
  ImageOutline,
  VideocamOutline,
  SaveOutline,
  SendOutline,
  ArrowUndoOutline,
  ArrowRedoOutline,
  ListOutline,
  ColorPaletteOutline
} from '@/icons'

defineProps<{
  hasActiveEditor: boolean
  saving: boolean
  isEdit: boolean
}>()

const emit = defineEmits<{
  insert: [type: ParagraphType]
  insertSeparator: []
  toggleCover: []
  saveDraft: []
  publish: []
  cancel: []
}>()

const showInsertDropdown = ref(false)

const insertTypes: { label: string; type: ParagraphType }[] = [
  { label: '图片', type: 'image' },
  { label: '视频', type: 'video' },
  { label: '代码', type: 'code' }
]

function handleClickInsert() {
  showInsertDropdown.value = !showInsertDropdown.value
}

function handleBlur() {
  setTimeout(() => {
    showInsertDropdown.value = false
  }, 150)
}

function selectType(type: ParagraphType) {
  showInsertDropdown.value = false
  emit('insert', type)
}
</script>

<template>
  <ArHBox
    gap="4px"
    align="center"
    style="
      padding: 4px 12px;
      background: var(--surface-color);
      border-bottom: 1px solid var(--border-color);
      position: sticky;
      top: 0;
      z-index: 10;
      min-height: 40px;
      user-select: none;
    "
  >
    <!-- ── 返回 ── -->
    <ArButton size="sm" type="ghost" icon @click="emit('cancel')" title="返回">
      <template #icon>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="15 18 9 12 15 6" />
        </svg>
      </template>
    </ArButton>

    <div class="toolbar-divider" />

    <!-- ── 字体样式：B / I / U ── -->
    <ArButton size="sm" type="ghost" icon :disabled="!hasActiveEditor" title="加粗">
      <template #icon>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M6 4h6a4 4 0 1 1 0 8H6z" />
          <path d="M6 12h7a4 4 0 1 1 0 8H6z" />
        </svg>
      </template>
    </ArButton>
    <ArButton size="sm" type="ghost" icon :disabled="!hasActiveEditor" title="斜体">
      <template #icon>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
          <line x1="17" y1="6" x2="10" y2="18" />
          <line x1="19" y1="6" x2="14" y2="6" />
          <line x1="10" y1="18" x2="5" y2="18" />
        </svg>
      </template>
    </ArButton>
    <ArButton size="sm" type="ghost" icon :disabled="!hasActiveEditor" title="下划线">
      <template #icon>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M6 4v6a6 6 0 0 0 12 0V4" />
          <line x1="4" y1="20" x2="20" y2="20" />
        </svg>
      </template>
    </ArButton>

    <div class="toolbar-divider" />

    <!-- ── 文字颜色 ── -->
    <ArButton size="sm" type="ghost" icon :disabled="!hasActiveEditor" title="文字颜色">
      <template #icon><ColorPaletteOutline /></template>
    </ArButton>

    <div class="toolbar-group-gap" />

    <!-- ── 对齐：左 / 中 / 右 ── -->
    <ArButton size="sm" type="ghost" icon :disabled="!hasActiveEditor" title="左对齐">
      <template #icon>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <line x1="3" y1="6" x2="21" y2="6" /><line x1="3" y1="10" x2="15" y2="10" /><line x1="3" y1="14" x2="19" y2="14" /><line x1="3" y1="18" x2="13" y2="18" />
        </svg>
      </template>
    </ArButton>
    <ArButton size="sm" type="ghost" icon :disabled="!hasActiveEditor" title="居中">
      <template #icon>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <line x1="3" y1="6" x2="21" y2="6" /><line x1="5" y1="10" x2="19" y2="10" /><line x1="3" y1="14" x2="21" y2="14" /><line x1="6" y1="18" x2="18" y2="18" />
        </svg>
      </template>
    </ArButton>
    <ArButton size="sm" type="ghost" icon :disabled="!hasActiveEditor" title="右对齐">
      <template #icon>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <line x1="3" y1="6" x2="21" y2="6" /><line x1="9" y1="10" x2="21" y2="10" /><line x1="5" y1="14" x2="21" y2="14" /><line x1="11" y1="18" x2="21" y2="18" />
        </svg>
      </template>
    </ArButton>

    <div class="toolbar-divider" />

    <!-- ── 列表 ── -->
    <ArButton size="sm" type="ghost" icon :disabled="!hasActiveEditor" title="无序列表">
      <template #icon><ListOutline /></template>
    </ArButton>

    <div class="toolbar-divider" />

    <!-- ── 插入（下拉） ── -->
    <div style="position: relative; display: inline-flex">
      <ArButton size="sm" type="ghost" icon @click="handleClickInsert" @blur="handleBlur" title="插入">
        <template #icon>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" />
          </svg>
        </template>
      </ArButton>
      <!-- 下拉菜单 -->
      <div
        v-if="showInsertDropdown"
        style="
          position: absolute;
          top: 100%;
          left: 0;
          margin-top: 4px;
          min-width: 100px;
          background: var(--surface-color);
          border: 1px solid var(--border-color);
          border-radius: var(--radius-md);
          box-shadow: var(--shadow-md);
          z-index: 20;
          overflow: hidden;
        "
      >
        <div
          v-for="item in insertTypes"
          :key="item.type"
          class="toolbar-dropdown-item"
          @mousedown.prevent="selectType(item.type)"
        >
          <ImageOutline v-if="item.type === 'image'" />
          <VideocamOutline v-if="item.type === 'video'" />
          <CodeSlashOutline v-if="item.type === 'code'" />
          {{ item.label }}
        </div>
        <!-- 分隔线选项 -->
        <div
          class="toolbar-dropdown-item toolbar-dropdown-item--with-top"
          @mousedown.prevent="emit('insertSeparator')"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
            <line x1="3" y1="12" x2="21" y2="12" />
          </svg>
          分隔线
        </div>
      </div>
    </div>

    <div style="flex: 1" />

    <!-- ── 右侧：封面 + 存草稿 + 发送 ── -->
    <ArButton size="sm" type="ghost" @click="emit('toggleCover')">
      <template #icon>
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
          <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
          <circle cx="8.5" cy="8.5" r="1.5" />
          <polyline points="21 15 16 10 5 21" />
        </svg>
      </template>
      封面
    </ArButton>

    <ArButton size="sm" type="secondary" :loading="saving" @click="emit('saveDraft')">
      <template #icon><SaveOutline /></template>
      存草稿
    </ArButton>

    <ArButton size="sm" type="primary" :loading="saving" @click="emit('publish')">
      <template #icon><SendOutline /></template>
      {{ isEdit ? '保存修改' : '发送' }}
    </ArButton>
  </ArHBox>
</template>

<style scoped>
.toolbar-divider {
  width: 1px;
  height: 20px;
  background: var(--divider-color);
  flex-shrink: 0;
  margin: 0 4px;
}

.toolbar-group-gap {
  width: 2px;
  flex-shrink: 0;
}

.toolbar-dropdown-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 14px;
  font-size: 13px;
  color: var(--text-primary);
  cursor: pointer;
  transition: background var(--transition-fast);
}

.toolbar-dropdown-item:hover {
  background: var(--primary-light-color);
}

.toolbar-dropdown-item--with-top {
  border-top: 1px solid var(--divider-color);
}
</style>
