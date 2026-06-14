<script setup lang="ts">
import { ref } from 'vue'
import ArButton from '@/components/ui/ArButton.vue'

withDefaults(
  defineProps<{
    loading?: boolean
    disabled?: boolean
  }>(),
  {
    loading: false,
    disabled: false
  }
)

const emit = defineEmits<{
  submit: [content: string]
}>()

const content = ref('')

function handleSubmit() {
  const trimmed = content.value.trim()
  if (!trimmed) return
  emit('submit', trimmed)
  content.value = ''
}

function canSubmit(): boolean {
  return content.value.trim().length > 0
}
</script>

<template>
  <div class="comment-form">
    <textarea
      v-model="content"
      class="form-textarea"
      :disabled="disabled"
      placeholder="写下你的评论……"
      rows="3"
      @keydown.meta.enter="handleSubmit"
      @keydown.ctrl.enter="handleSubmit"
    />
    <div class="form-actions">
      <ArButton
        type="primary"
        size="sm"
        :loading="loading"
        :disabled="!canSubmit() || disabled"
        @click="handleSubmit"
      >
        发表评论
      </ArButton>
    </div>
  </div>
</template>

<style scoped>
.comment-form {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.form-textarea {
  width: 100%;
  padding: var(--spacing-sm) var(--spacing-md);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  background: var(--surface-inset-color);
  color: var(--text-primary);
  font-family: var(--font-sans);
  font-size: 14px;
  line-height: 1.6;
  resize: vertical;
  outline: none;
  transition:
    border-color var(--transition-fast),
    box-shadow var(--transition-fast);
}

.form-textarea:focus {
  border-color: var(--primary-color);
  box-shadow: 0 0 0 3px var(--primary-light-color);
}

.form-textarea::placeholder {
  color: var(--text-tertiary);
}

.form-textarea:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
}
</style>
