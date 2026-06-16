<script setup lang="ts">
/**
 * EditorPaper — 纸面布局容器
 *
 * Apple Notes 式居中纸面布局，无段落相关逻辑。
 * 提供滚动容器 + 白底阴影纸面 + 编辑器内容样式。
 */
</script>

<template>
  <div class="editor-desk">
    <div class="editor-paper">
      <div class="editor-prose">
        <slot />
      </div>
    </div>
  </div>
</template>

<style scoped>
.editor-desk {
  flex: 1;
  overflow-y: auto;
}

.editor-paper {
  max-width: 880px;
  width: 100%;
  margin: var(--spacing-lg) auto;
  padding: var(--spacing-lg) var(--spacing-xl);
  min-height: calc(100vh - 120px);
  background: var(--paper-color);
  box-shadow: var(--paper-shadow);
  border-radius: var(--radius-lg);
}

/* ProseMirror 内容样式 */
.editor-prose :deep(.ProseMirror) {
  min-height: 400px;
  outline: none;
  font-size: 1.05em;
  line-height: 1.8;
  color: var(--text-primary);
  font-family: var(--font-serif);
}

.editor-prose :deep(.ProseMirror p) {
  margin: 0.5em 0;
}

.editor-prose :deep(.ProseMirror h1) {
  font-size: 1.8em;
  font-weight: var(--font-weight-bold);
  margin: 0.8em 0 0.4em;
}

.editor-prose :deep(.ProseMirror h2) {
  font-size: 1.5em;
  font-weight: var(--font-weight-bold);
  margin: 0.7em 0 0.3em;
}

.editor-prose :deep(.ProseMirror h3) {
  font-size: 1.25em;
  font-weight: var(--font-weight-semibold);
  margin: 0.6em 0 0.3em;
}

.editor-prose :deep(.ProseMirror ul),
.editor-prose :deep(.ProseMirror ol) {
  padding-left: 1.5em;
}

.editor-prose :deep(.ProseMirror blockquote) {
  border-left: 3px solid var(--border-color);
  padding-left: var(--spacing-md);
  color: var(--text-secondary);
  font-style: italic;
  margin: 0.5em 0;
}

.editor-prose :deep(.ProseMirror pre) {
  background: var(--surface-hover-color);
  border-radius: var(--radius-sm);
  padding: var(--spacing-md);
  font-family: var(--font-mono);
  font-size: 0.9em;
  overflow-x: auto;
}

.editor-prose :deep(.ProseMirror img) {
  max-width: 100%;
  height: auto;
  border-radius: var(--radius-sm);
  margin: var(--spacing-md) 0;
}

.editor-prose :deep(.ProseMirror p.is-editor-empty:first-child::before) {
  color: var(--text-tertiary);
  content: attr(data-placeholder);
  float: left;
  height: 0;
  pointer-events: none;
}
</style>
