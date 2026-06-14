<script setup lang="ts">
/**
 * EditorFooter — 编辑器底部发布栏
 *
 * 封面设置、标签管理、可见等级、保存/发布按钮。
 * 点击"发布设置"展开抽屉面板展示更多选项。
 */
import { ref } from 'vue'
import ArVBox from '@/components/ui/ArVBox.vue'
import ArHBox from '@/components/ui/ArHBox.vue'
import ArButton from '@/components/ui/ArButton.vue'
import ArInput from '@/components/ui/ArInput.vue'
import ArTag from '@/components/ui/ArTag.vue'
import CoverUploader from './CoverUploader.vue'

defineProps<{
  coverUrl: string
  tags: string[]
  requiredLevel: number
  saving: boolean
  isEdit: boolean
}>()

const emit = defineEmits<{
  'update:coverUrl': [value: string]
  addTag: [name: string]
  removeTag: [name: string]
  'update:requiredLevel': [level: number]
  save: []
  cancel: []
}>()

const tagInput = ref('')
const showPanel = ref(false)

function handleTagKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter') {
    e.preventDefault()
    const val = tagInput.value.trim()
    if (val) {
      emit('addTag', val)
      tagInput.value = ''
    }
  }
}

function addTag() {
  const val = tagInput.value.trim()
  if (val) {
    emit('addTag', val)
    tagInput.value = ''
  }
}

const levelOptions = [
  { value: 0, label: 'P0 - 仅管理员' },
  { value: 1, label: 'P1' },
  { value: 2, label: 'P2' },
  { value: 3, label: 'P3' },
  { value: 4, label: 'P4' },
  { value: 5, label: 'P5 - 所有人' }
]
</script>

<template>
  <ArVBox style="border-top: 1px solid var(--border-color); background: var(--surface-color)">
    <!-- 折叠面板：发布设置 -->
    <ArVBox
      v-if="showPanel"
      gap="var(--spacing-md)"
      style="
        padding: var(--spacing-md) var(--spacing-lg);
        border-bottom: 1px solid var(--border-color);
        background: var(--surface-inset-color);
      "
    >
      <ArHBox gap="var(--spacing-sm)" align="start">
        <span
          style="
            width: 64px;
            flex-shrink: 0;
            font-size: 13px;
            font-weight: var(--font-weight-semibold);
            color: var(--text-secondary);
            padding-top: 6px;
          "
          >封面</span
        >
        <CoverUploader
          :cover-url="coverUrl"
          style="flex: 1"
          @update:cover-url="emit('update:coverUrl', $event)"
        />
      </ArHBox>

      <ArHBox gap="var(--spacing-sm)" align="start">
        <span
          style="
            width: 64px;
            flex-shrink: 0;
            font-size: 13px;
            font-weight: var(--font-weight-semibold);
            color: var(--text-secondary);
            padding-top: 6px;
          "
          >标签</span
        >
        <ArVBox gap="6px" style="flex: 1">
          <ArHBox gap="6px">
            <ArInput
              v-model:value="tagInput"
              placeholder="输入标签后按 Enter"
              size="sm"
              style="flex: 1"
              @keydown="handleTagKeydown"
            />
            <ArButton size="sm" type="secondary" @click="addTag">添加</ArButton>
          </ArHBox>
          <ArHBox v-if="tags.length > 0" gap="4px" wrap>
            <ArTag
              v-for="tag in tags"
              :key="tag"
              color="primary"
              size="sm"
              type="light"
              closable
              @close="emit('removeTag', tag)"
            >
              {{ tag }}
            </ArTag>
          </ArHBox>
        </ArVBox>
      </ArHBox>

      <ArHBox gap="var(--spacing-sm)" align="start">
        <span
          style="
            width: 64px;
            flex-shrink: 0;
            font-size: 13px;
            font-weight: var(--font-weight-semibold);
            color: var(--text-secondary);
            padding-top: 6px;
          "
          >可见等级</span
        >
        <select
          :value="requiredLevel"
          style="
            padding: 6px 10px;
            border: 1px solid var(--border-color);
            border-radius: var(--radius-sm);
            background: var(--surface-color);
            color: var(--text-primary);
            font-size: 13px;
          "
          @change="emit('update:requiredLevel', Number(($event.target as HTMLSelectElement).value))"
        >
          <option v-for="opt in levelOptions" :key="opt.value" :value="opt.value">
            {{ opt.label }}
          </option>
        </select>
      </ArHBox>
    </ArVBox>

    <!-- 底部操作栏 -->
    <ArHBox
      gap="var(--spacing-sm)"
      justify="space-between"
      style="padding: var(--spacing-sm) var(--spacing-lg)"
    >
      <ArButton type="ghost" @click="emit('cancel')">取消</ArButton>
      <ArHBox gap="var(--spacing-sm)">
        <ArButton type="ghost" @click="showPanel = !showPanel">
          {{ showPanel ? '收起设置' : '发布设置' }}
        </ArButton>
        <ArButton type="primary" :loading="saving" @click="emit('save')">
          {{ isEdit ? '保存修改' : '发布' }}
        </ArButton>
      </ArHBox>
    </ArHBox>
  </ArVBox>
</template>
