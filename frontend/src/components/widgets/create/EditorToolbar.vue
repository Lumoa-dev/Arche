<script setup lang="ts">
/**
 * EditorToolbar — 编辑器顶部工具栏
 *
 * 集成所有操作：返回/取消、字体样式、插入段落、封面设置、存草稿、发送。
 * 不再有底部栏，一切操作集中在此。
 */
import { ref } from 'vue'
import ArHBox from '@/components/ui/ArHBox.vue'
import ArButton from '@/components/ui/ArButton.vue'
import type { ParagraphType } from '@/components/logic/useParagraphEditor'

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
  { label: '文本', type: 'text' },
  { label: '标题', type: 'heading' },
  { label: '图片', type: 'image' },
  { label: '视频', type: 'video' },
  { label: '代码', type: 'code' }
]

function handleDragStart(e: DragEvent) {
  if (e.dataTransfer) {
    e.dataTransfer.setData('paragraph-type', 'text')
    e.dataTransfer.effectAllowed = 'copy'
  }
}

function selectType(type: ParagraphType) {
  showInsertDropdown.value = false
  emit('insert', type)
}

function handleClickInsert() {
  showInsertDropdown.value = !showInsertDropdown.value
}

function handleBlur() {
  setTimeout(() => {
    showInsertDropdown.value = false
  }, 150)
}
</script>

<template>
  <ArHBox
    gap="6px"
    align="center"
    style="
      padding: 6px 16px;
      background: var(--surface-color);
      border-bottom: 2px solid var(--border-color);
      position: sticky;
      top: 0;
      z-index: 10;
      min-height: 44px;
      user-select: none;
    "
  >
    <!-- ── 左侧：取消/返回 ── -->
    <ArButton size="sm" type="ghost" @click="emit('cancel')"> ← 取消 </ArButton>

    <div
      style="
        width: 1px;
        height: 22px;
        background: var(--divider-color);
        flex-shrink: 0;
        margin: 0 4px;
      "
    />

    <!-- ── 字体样式 ── -->
    <ArHBox gap="2px" style="flex-shrink: 0">
      <ArButton size="sm" type="ghost" :disabled="!hasActiveEditor">
        <strong>B</strong>
      </ArButton>
      <ArButton size="sm" type="ghost" :disabled="!hasActiveEditor">
        <em>I</em>
      </ArButton>
      <ArButton size="sm" type="ghost" :disabled="!hasActiveEditor">
        <u>U</u>
      </ArButton>
    </ArHBox>

    <div
      style="
        width: 1px;
        height: 22px;
        background: var(--divider-color);
        flex-shrink: 0;
        margin: 0 4px;
      "
    />

    <!-- ── 插入 ── -->
    <div
      draggable="true"
      style="position: relative; display: inline-flex"
      @dragstart="handleDragStart"
    >
      <ArButton size="sm" type="secondary" @click="handleClickInsert" @blur="handleBlur">
        插入 ▼
      </ArButton>
      <!-- 下拉菜单 -->
      <div
        v-if="showInsertDropdown"
        style="
          position: absolute;
          top: 100%;
          left: 0;
          margin-top: 4px;
          min-width: 120px;
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
          style="
            padding: 8px 14px;
            font-size: 13px;
            color: var(--text-primary);
            cursor: pointer;
            transition: background var(--transition-fast);
          "
          @mousedown.prevent="selectType(item.type)"
        >
          {{ item.label }}
        </div>
      </div>
    </div>

    <!-- ── 分隔线 ── -->
    <ArButton size="sm" type="ghost" @click="emit('insertSeparator')"> 分隔线 </ArButton>

    <div style="flex: 1" />

    <!-- ── 右侧：封面 + 存草稿 + 发送 ── -->
    <ArButton size="sm" type="ghost" @click="emit('toggleCover')"> 封面 </ArButton>

    <ArButton size="sm" type="secondary" :loading="saving" @click="emit('saveDraft')">
      存草稿
    </ArButton>

    <ArButton size="sm" type="primary" :loading="saving" @click="emit('publish')">
      {{ isEdit ? '保存修改' : '发送' }}
    </ArButton>
  </ArHBox>
</template>
