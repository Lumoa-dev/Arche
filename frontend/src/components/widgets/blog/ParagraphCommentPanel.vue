<script setup lang="ts">
import { ref, watch } from 'vue'
import CommentForm from './CommentForm.vue'
import CommentList from './CommentList.vue'
import type { BlogComment } from '@/components/logic/api'
import type { ParagraphData } from '@/components/logic/api'

const props = withDefaults(
  defineProps<{
    visible?: boolean
    paragraph?: ParagraphData | null
    comments?: BlogComment[]
    loading?: boolean
    posting?: boolean
    isLoggedIn?: boolean
  }>(),
  {
    visible: false,
    paragraph: null,
    comments: () => [],
    loading: false,
    posting: false,
    isLoggedIn: false
  }
)

const emit = defineEmits<{
  close: []
  submitComment: [content: string]
}>()

const panelRef = ref<HTMLElement | null>(null)

// 点击面板外关闭
function handleClickOutside(e: MouseEvent) {
  if (panelRef.value && !panelRef.value.contains(e.target as Node)) {
    emit('close')
  }
}

watch(
  () => props.visible,
  (val) => {
    if (val) {
      document.addEventListener('click', handleClickOutside, true)
    } else {
      document.removeEventListener('click', handleClickOutside, true)
    }
  }
)

function handleSubmit(content: string) {
  emit('submitComment', content)
}
</script>

<template>
  <Transition name="panel">
    <div v-if="visible && paragraph" class="panel-overlay">
      <div ref="panelRef" class="paragraph-panel">
        <!-- 头部 -->
        <div class="panel-header">
          <h3 class="panel-title">
            段落评论 <span class="panel-index">#{{ paragraph.pid }}</span>
          </h3>
          <button class="panel-close" @click="emit('close')" aria-label="关闭">&times;</button>
        </div>

        <!-- 段落原文引用 -->
        <!-- eslint-disable-next-line vue/no-v-html -->
        <div class="paragraph-quote" v-html="paragraph.content" />

        <!-- 评论列表 -->
        <div class="panel-comments">
          <div v-if="loading" class="panel-loading">加载中……</div>
          <CommentList v-else :comments="comments" />
        </div>

        <!-- 评论输入 -->
        <div class="panel-input">
          <CommentForm v-if="isLoggedIn" :loading="posting" @submit="handleSubmit" />
          <div v-else class="login-hint">登录后即可发表段落评论</div>
        </div>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.panel-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.3);
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
}

.paragraph-panel {
  width: 520px;
  max-height: 80vh;
  background: var(--surface-color);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-color);
  box-shadow: var(--shadow-lg);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  animation: panel-in 0.2s var(--ease-out-smooth);
}

@keyframes panel-in {
  from {
    opacity: 0;
    transform: translateY(12px) scale(0.98);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

/* ── 头部 ── */
.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-md) var(--spacing-lg);
  border-bottom: 1px solid var(--divider-color);
}

.panel-title {
  margin: 0;
  font-size: 15px;
  font-weight: var(--font-weight-semibold);
  color: var(--text-primary);
}

.panel-close {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  background: transparent;
  font-size: 20px;
  color: var(--text-tertiary);
  cursor: pointer;
  border-radius: var(--radius-sm);
  transition: all var(--transition-fast);
}

.panel-close:hover {
  background: var(--surface-hover-color);
  color: var(--text-primary);
}

.panel-index {
  display: inline-block;
  margin-left: 6px;
  padding: 0 6px;
  font-size: 11px;
  font-weight: var(--font-weight-semibold);
  color: var(--text-tertiary);
  background: var(--surface-inset-color);
  border-radius: var(--radius-sm);
  font-family: var(--font-mono, var(--font-sans));
}

/* ── 段落引用 ── */
.paragraph-quote {
  padding: var(--spacing-sm) var(--spacing-lg);
  font-family: var(--font-serif);
  font-size: 14px;
  line-height: 1.8;
  color: var(--text-secondary);
  background: var(--surface-inset-color);
  border-bottom: 1px solid var(--divider-color);
  max-height: 120px;
  overflow-y: auto;
  white-space: pre-wrap;
  word-break: break-word;
}

/* ── 评论列表 ── */
.panel-comments {
  flex: 1;
  overflow-y: auto;
  padding: var(--spacing-md) var(--spacing-lg);
  min-height: 100px;
}

.panel-loading {
  text-align: center;
  padding: var(--spacing-2xl) 0;
  font-size: 13px;
  color: var(--text-tertiary);
}

/* ── 输入区域 ── */
.panel-input {
  padding: var(--spacing-md) var(--spacing-lg);
  border-top: 1px solid var(--divider-color);
}

.login-hint {
  text-align: center;
  padding: var(--spacing-md) 0;
  font-size: 13px;
  color: var(--text-tertiary);
}

/* ── 过渡动画 ── */
.panel-enter-active,
.panel-leave-active {
  transition: opacity 0.2s ease;
}

.panel-enter-from,
.panel-leave-to {
  opacity: 0;
}
</style>
