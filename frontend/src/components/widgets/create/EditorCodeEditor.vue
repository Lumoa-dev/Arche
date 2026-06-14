<script setup lang="ts">
/**
 * EditorCodeEditor — 代码卡片编辑区
 *
 * 等宽字体编辑区，纯文本内容。
 */
import { ref, watch } from 'vue'

const props = defineProps<{
  content: string
}>()

const emit = defineEmits<{
  'update:content': [value: string]
}>()

const codeText = ref(props.content || '')

watch(
  () => props.content,
  (val) => {
    if (val !== codeText.value) codeText.value = val || ''
  }
)

function handleInput(e: Event) {
  const val = (e.target as HTMLTextAreaElement).value
  codeText.value = val
  emit('update:content', val)
}
</script>

<template>
  <div class="code-editor">
    <textarea
      :value="codeText"
      class="code-textarea"
      placeholder="输入代码……"
      spellcheck="false"
      @input="handleInput"
    />
  </div>
</template>

<style scoped>
.code-editor {
  padding: 0;
}

.code-textarea {
  width: 100%;
  min-height: 100px;
  padding: 12px 16px;
  border: none;
  background: #1a1817;
  color: #e0ddd7;
  font-family: var(--font-mono, 'Fira Code', 'Consolas', 'Monaco', monospace);
  font-size: 13.5px;
  line-height: 1.7;
  outline: none;
  resize: vertical;
  tab-size: 2;
}

.code-textarea::placeholder {
  color: rgba(224, 221, 215, 0.35);
}
</style>
