<script setup lang="ts">
/**
 * EditorLayout — 编辑器工作台布局
 *
 * 提供编辑器所需的 flex 布局结构，所有布局 CSS 集中于此。
 * 即插即用，页面只需填入各 slot。
 */
</script>

<template>
  <div class="edit-layout">
    <slot name="sidebar" />
    <main class="edit-main">
      <slot name="topbar" />
      <div class="edit-body">
        <div class="edit-editor">
          <slot name="editor" />
        </div>
        <div class="sidebar-inner">
          <slot name="sidebar-inner" />
        </div>
      </div>
    </main>
  </div>
</template>

<style scoped>
.edit-layout {
  display: flex;
  height: calc(100vh - 56px - var(--content-padding) * 2);
  margin: calc(-1 * var(--content-padding));
  overflow: hidden;
}
.edit-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.edit-body {
  display: flex;
  flex: 1;
  min-height: 0;
  overflow: hidden;
}
.edit-editor {
  flex: 1;
  overflow-y: auto;
  padding: var(--spacing-lg);
}
.sidebar-inner {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-lg);
  height: 100%;
  overflow-y: auto;
}
</style>
