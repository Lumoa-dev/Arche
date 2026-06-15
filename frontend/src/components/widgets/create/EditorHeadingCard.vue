<script setup lang="ts">
/**
 * EditorHeadingCard — 段标题卡片
 *
 * 显示 ## / ### 段标题，带层级样式。
 * 非富文本编辑——段标题的本身定位是"章节标记"，不需要复杂格式。
 * 点击可编辑标题文字（轻量 inline editing）。
 */
import { ref, nextTick } from 'vue'

const props = defineProps<{
  content: string
  level?: number // 2 or 3
}>()

const emit = defineEmits<{
  'update:content': [value: string]
}>()

const editing = ref(false)
const editText = ref('')
const inputRef = ref<HTMLInputElement | null>(null)

function startEdit() {
  editText.value = props.content
  editing.value = true
  nextTick(() => inputRef.value?.focus())
}

function saveEdit() {
  const val = editText.value.trim()
  if (val && val !== props.content) {
    emit('update:content', val)
  }
  editing.value = false
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter') saveEdit()
  if (e.key === 'Escape') editing.value = false
}
</script>

<template>
  <div
    class="heading-card"
    :class="[`heading-card--h${level || 2}`, { 'heading-card--editing': editing }]"
    @dblclick="startEdit"
  >
    <input
      v-if="editing"
      ref="inputRef"
      v-model="editText"
      class="heading-card__input"
      @blur="saveEdit"
      @keydown="onKeydown"
    />
    <div v-else class="heading-card__text">
      <span class="heading-card__prefix">{{ 'H' + (level || 2) }}</span>
      <span>{{ content || '（空标题）' }}</span>
    </div>
  </div>
</template>

<style scoped>
.heading-card {
  padding: 8px 20px;
  user-select: none;
}

.heading-card__text {
  display: flex;
  align-items: baseline;
  gap: 10px;
}

.heading-card__prefix {
  font-size: 11px;
  font-weight: var(--font-weight-semibold);
  color: var(--text-tertiary);
  background: var(--surface-hover-color);
  padding: 1px 7px;
  border-radius: 4px;
  flex-shrink: 0;
  line-height: 20px;
}

/* H2 样式 */
.heading-card--h2 .heading-card__text {
  font-size: 20px;
  font-weight: var(--font-weight-bold);
  color: var(--text-primary);
  font-family: var(--font-serif);
  line-height: 1.4;
}

/* H3 样式 */
.heading-card--h3 .heading-card__text {
  font-size: 17px;
  font-weight: var(--font-weight-semibold);
  color: var(--text-secondary);
  line-height: 1.4;
}

/* 编辑模式 */
.heading-card__input {
  width: 100%;
  border: none;
  outline: none;
  background: transparent;
  font-size: inherit;
  font-weight: inherit;
  font-family: inherit;
  color: inherit;
  padding: 2px 0;
  border-bottom: 1px solid var(--primary-color);
}

.heading-card--editing {
  cursor: text;
}
</style>
