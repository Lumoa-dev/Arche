<script setup lang="ts">
import { ref, computed } from 'vue'
import ArInput from '@/components/ui/ArInput.vue'
import ArButton from '@/components/ui/ArButton.vue'
import ArTag from '@/components/ui/ArTag.vue'
import RichTextEditor from './RichTextEditor.vue'
import type { BlogPost, CreatePostPayload, UpdatePostPayload } from '@/components/logic/api'

const props = withDefaults(
  defineProps<{
    post?: BlogPost | null
    loading?: boolean
    hideFooter?: boolean
    coverUrl?: string
  }>(),
  {
    post: null,
    loading: false,
    hideFooter: false,
    coverUrl: ''
  }
)

const emit = defineEmits<{
  save: [payload: CreatePostPayload | UpdatePostPayload]
  cancel: []
  'update:coverUrl': [value: string]
}>()

const isEdit = computed(() => !!props.post)

const title = ref(props.post?.title || '')
const intro = ref(props.post?.intro || '')
const content = ref(props.post?.content || '')
const tagInput = ref('')
const tags = ref<string[]>(props.post?.tags || [])
const requiredLevel = ref<number>(props.post?.required_level ?? 5)

const canSubmit = computed(() => title.value.trim().length > 0 && content.value.trim().length > 0)

function addTag() {
  const t = tagInput.value.trim()
  if (t && !tags.value.includes(t)) {
    tags.value.push(t)
  }
  tagInput.value = ''
}

function removeTag(tag: string) {
  tags.value = tags.value.filter((t) => t !== tag)
}

function handleTagKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' || e.key === ',') {
    e.preventDefault()
    addTag()
  }
}

function handleSave() {
  if (!canSubmit.value) return
  const payload: CreatePostPayload | UpdatePostPayload = isEdit.value
    ? {
        title: title.value.trim(),
        ...(intro.value.trim() ? { intro: intro.value.trim() } : {}),
        content: content.value.trim(),
        ...(props.coverUrl ? { cover_url: props.coverUrl } : {})
      }
    : {
        title: title.value.trim(),
        ...(intro.value.trim() ? { intro: intro.value.trim() } : {}),
        content: content.value.trim(),
        tags: tags.value,
        required_level: requiredLevel.value,
        ...(props.coverUrl ? { cover_url: props.coverUrl } : {})
      }
  emit('save', payload)
}

function handleCancel() {
  emit('cancel')
}

function updateMeta(meta: { tags?: string[]; requiredLevel?: number }) {
  if (meta.tags) tags.value = meta.tags
  if (meta.requiredLevel !== undefined) requiredLevel.value = meta.requiredLevel
}

defineExpose({
  handleSave,
  handleCancel,
  tags,
  tagInput,
  addTag,
  removeTag,
  handleTagKeydown,
  requiredLevel,
  title,
  intro,
  content,
  updateMeta
})
</script>

<template>
  <div class="post-editor">
    <!-- 标题 -->
    <div class="editor-field">
      <label class="field-label">标题</label>
      <ArInput
        v-model:value="title"
        placeholder="输入文章标题……"
        size="large"
        :maxlength="120"
        show-count
      />
    </div>

    <!-- 引言 -->
    <div class="editor-field">
      <label class="field-label"
        >引言 <span class="field-optional">（可选，用作文字封面素材）</span></label
      >
      <textarea
        v-model="intro"
        class="field-textarea"
        placeholder="用一两句话概括文章精华……"
        rows="2"
        maxlength="512"
      />
      <span class="field-hint">未填写时将从正文自动截取</span>
    </div>

    <!-- 内容 -->
    <div class="editor-field">
      <label class="field-label">正文</label>
      <RichTextEditor v-model="content" placeholder="开始写下你的想法……" />
    </div>

    <!-- 标签 -->
    <div v-if="!hideFooter" class="editor-field">
      <label class="field-label">标签</label>
      <div class="tag-input-row">
        <ArInput
          v-model:value="tagInput"
          placeholder="输入标签后按 Enter 添加"
          size="small"
          @keydown="handleTagKeydown"
        />
        <ArButton size="sm" type="secondary" @click="addTag">添加</ArButton>
      </div>
      <div v-if="tags.length > 0" class="tag-list">
        <ArTag
          v-for="tag in tags"
          :key="tag"
          color="primary"
          size="sm"
          type="light"
          closable
          @close="removeTag(tag)"
        >
          {{ tag }}
        </ArTag>
      </div>
    </div>

    <!-- 可见等级（仅新建模式） -->
    <div v-if="!isEdit && !hideFooter" class="editor-field">
      <label class="field-label">可见等级（P0=管理员 · P5=所有人）</label>
      <select v-model.number="requiredLevel" class="field-select">
        <option :value="0">P0 - 仅管理员</option>
        <option :value="1">P1</option>
        <option :value="2">P2</option>
        <option :value="3">P3</option>
        <option :value="4">P4</option>
        <option :value="5">P5 - 所有人</option>
      </select>
    </div>

    <!-- 操作按钮 -->
    <div v-if="!hideFooter" class="editor-actions">
      <ArButton type="ghost" @click="handleCancel">取消</ArButton>
      <ArButton type="primary" :loading="loading" :disabled="!canSubmit" @click="handleSave">
        {{ isEdit ? '保存修改' : '发布' }}
      </ArButton>
    </div>
  </div>
</template>

<style scoped>
.post-editor {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-lg);
  font-family: var(--font-sans);
}

.editor-field {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.field-label {
  font-size: 14px;
  font-weight: var(--font-weight-semibold);
  color: var(--text-primary);
}

.field-optional {
  font-weight: var(--font-weight-normal);
  font-size: 12px;
  color: var(--text-tertiary);
}

.field-hint {
  font-size: 12px;
  color: var(--text-quaternary);
  line-height: 1.4;
}

.field-textarea {
  width: 100%;
  min-height: 56px;
  padding: 10px 12px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  background: var(--surface-color);
  color: var(--text-primary);
  font-family: var(--font-sans);
  font-size: 14px;
  line-height: 1.5;
  outline: none;
  resize: vertical;
  transition: border-color var(--transition-fast);
}

.field-textarea:focus {
  border-color: var(--primary-color);
  box-shadow: 0 0 0 3px var(--primary-light-color);
}

.field-textarea::placeholder {
  color: var(--text-quaternary);
}

.tag-input-row {
  display: flex;
  gap: var(--spacing-sm);
}

.tag-input-row .ar-input {
  flex: 1;
}

.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: var(--spacing-xs);
}

.field-select {
  width: 100%;
  max-width: 240px;
  padding: 8px 12px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  background: var(--surface-color);
  color: var(--text-primary);
  font-family: var(--font-sans);
  font-size: 14px;
  outline: none;
  cursor: pointer;
  transition: border-color var(--transition-fast);
  appearance: auto;
}

.field-select:focus {
  border-color: var(--primary-color);
  box-shadow: 0 0 0 3px var(--primary-light-color);
}

.editor-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--spacing-sm);
  padding-top: var(--spacing-md);
  border-top: 1px solid var(--border-color);
}
</style>
