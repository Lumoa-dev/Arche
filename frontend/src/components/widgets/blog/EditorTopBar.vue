<script setup lang="ts">
/**
 * EditorTopBar — 编辑器顶栏
 *
 * 包含状态标签、标签编辑器、访问权限滚轮选择器和保存/取消按钮。
 * 标签输入状态（tagInputValue）内部管理，通过 update:tags 发射变更。
 */
import { ref } from 'vue'
import ArTag from '@/components/ui/ArTag.vue'
import ArWheelPicker from '@/components/ui/ArWheelPicker.vue'
import ArButton from '@/components/ui/ArButton.vue'

const props = withDefaults(
  defineProps<{
    status?: string | null
    isNew?: boolean
    tags?: string[]
    access?: number
  }>(),
  {
    status: null,
    isNew: false,
    tags: () => [],
    access: 5
  }
)

const emit = defineEmits<{
  'update:tags': [tags: string[]]
  'update:access': [access: number]
  save: []
  cancel: []
}>()

const tagInputValue = ref('')

const statusMap: Record<string, { label: string; color: 'green' | 'yellow' | 'blue' | 'default' }> =
  {
    published: { label: '已发布', color: 'green' },
    pending: { label: '审核中', color: 'yellow' },
    draft: { label: '草稿', color: 'blue' }
  }

function getStatus(postStatus: string | null) {
  const s = postStatus || 'draft'
  return statusMap[s] || { label: s, color: 'default' as const }
}

function addTag() {
  const t = tagInputValue.value.trim()
  if (t && !props.tags.includes(t)) {
    emit('update:tags', [...props.tags, t])
  }
  tagInputValue.value = ''
}

function removeTag(tag: string) {
  emit(
    'update:tags',
    props.tags.filter((t) => t !== tag)
  )
}

function handleTagKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' || e.key === ',') {
    e.preventDefault()
    addTag()
  }
}

function handleAccessUpdate(value: string) {
  emit('update:access', Number(value))
}
</script>

<template>
  <div class="edit-topbar">
    <div class="edit-topbar-left">
      <template v-if="isNew">
        <span class="topbar-label">新建文章</span>
      </template>
      <ArTag v-else :color="getStatus(status).color" type="light">
        {{ getStatus(status).label }}
      </ArTag>
      <ArWheelPicker
        :options="['0', '1', '2', '3', '4', '5']"
        :model-value="String(access)"
        title="帖子可见权限：P0=仅管理员 · P5=所有人可见"
        @update:model-value="handleAccessUpdate"
      />
    </div>
    <div class="edit-topbar-tags">
      <TransitionGroup name="tag-enter" tag="div" class="topbar-tag-list">
        <ArTag
          v-for="tag in tags"
          :key="tag"
          color="primary"
          type="light"
          closable
          @close="removeTag(tag)"
        >
          {{ tag }}
        </ArTag>
      </TransitionGroup>
      <input
        v-model="tagInputValue"
        class="tag-input-inline"
        placeholder="标签"
        @keydown="handleTagKeydown"
      />
    </div>
    <div class="edit-topbar-actions">
      <ArButton type="ghost" @click="emit('cancel')">取消</ArButton>
      <ArButton type="primary" @click="emit('save')">
        {{ isNew ? '发布' : '保存' }}
      </ArButton>
    </div>
  </div>
</template>

<style scoped>
.edit-topbar {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 10px 20px;
  border-bottom: 1px solid var(--border-color);
  background: var(--surface-color);
  flex-shrink: 0;
  flex-wrap: wrap;
}

.edit-topbar-left {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.topbar-label {
  font-size: 14px;
  font-weight: var(--font-weight-medium);
  color: var(--text-primary);
}

.edit-topbar-tags {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 140px;
}

.topbar-tag-list {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.tag-input-inline {
  border: none;
  border-bottom: 1px solid var(--border-color);
  outline: none;
  background: transparent;
  color: var(--text-primary);
  font-family: var(--font-sans);
  font-size: 13px;
  padding: 4px 0;
  min-width: 70px;
  flex: 1;
  transition: border-color var(--transition-fast);
}

.tag-input-inline:focus {
  border-bottom-color: var(--primary-color);
}

.tag-input-inline::placeholder {
  color: var(--text-tertiary);
}

.tag-enter-enter-active {
  transition: all 0.25s var(--ease-out-smooth);
}
.tag-enter-leave-active {
  transition: all 0.2s ease-in;
}
.tag-enter-enter-from {
  opacity: 0;
  transform: scale(0.7);
}
.tag-enter-leave-to {
  opacity: 0;
  transform: scale(0.7);
}

.edit-topbar-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}
</style>
