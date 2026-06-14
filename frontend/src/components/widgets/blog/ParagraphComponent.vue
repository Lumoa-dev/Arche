<script setup lang="ts">
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import type { ParagraphData } from '@/components/logic/api'

defineProps<{
  paragraph: ParagraphData
  index: number
}>()

const emit = defineEmits<{
  click: [paragraph: ParagraphData]
}>()

function renderContent(text: string): string {
  const html = marked.parse(text, { gfm: true }) as string
  return DOMPurify.sanitize(html)
}
</script>

<!-- eslint-disable vue/no-v-html -->
<template>
  <div
    class="paragraph-component"
    :class="`paragraph--${paragraph.type}`"
    @click="emit('click', paragraph)"
  >
    <span class="paragraph-index">{{ index }}</span>
    <div
      v-if="paragraph.type === 'text'"
      class="paragraph-text"
      v-html="renderContent(paragraph.content)"
    />
    <pre
      v-else-if="paragraph.type === 'code'"
      class="paragraph-code"
    ><code>{{ paragraph.content }}</code></pre>
    <figure v-else-if="paragraph.type === 'image'" class="paragraph-image">
      <img :src="paragraph.media_url" :alt="paragraph.caption || ''" loading="lazy" />
      <figcaption v-if="paragraph.caption">{{ paragraph.caption }}</figcaption>
    </figure>
    <blockquote v-else-if="paragraph.type === 'quote'" class="paragraph-quote">
      <p>{{ paragraph.content }}</p>
    </blockquote>
    <h3 v-else-if="paragraph.type === 'heading'" class="paragraph-heading">
      {{ paragraph.content }}
    </h3>
    <div v-else class="paragraph-text" v-html="renderContent(paragraph.content)" />
  </div>
</template>
<!-- eslint-enable vue/no-v-html -->

<style scoped>
.paragraph-component {
  position: relative;
  padding: 4px 0 4px 32px;
  margin: 0 0 0.6em;
  cursor: pointer;
  border-radius: var(--radius-sm);
  transition: background-color var(--transition-fast);
  font-family: var(--font-serif);
  font-size: 16.5px;
  line-height: 2;
  color: var(--text-primary);
  word-break: break-word;
}

.paragraph-component:hover {
  background: var(--surface-hover-color);
}

/* 段落编号 */
.paragraph-index {
  position: absolute;
  left: 0;
  top: 6px;
  width: 26px;
  text-align: right;
  padding-right: 6px;
  font-family: var(--font-mono, var(--font-sans));
  font-size: 11px;
  color: var(--text-quaternary);
  user-select: none;
  opacity: 0.45;
  transition: opacity var(--transition-fast);
}

.paragraph-component:hover .paragraph-index {
  opacity: 0.85;
}

/* ── text 类型 ── */
.paragraph-text {
  display: block;
}

.paragraph-text :deep(.media-block) {
  margin: 0;
  text-align: center;
}

.paragraph-text :deep(.image-block) {
  margin: 1.5em 0;
}

.paragraph-text :deep(.image-block img) {
  max-width: 100%;
  width: 100%;
  max-width: 720px;
  border-radius: var(--radius-md);
  display: block;
  margin: 0 auto;
}

.paragraph-text :deep(.video-block) {
  position: relative;
  width: 100%;
  aspect-ratio: 16 / 9;
  margin: 1.5em 0;
  border-radius: var(--radius-md);
  overflow: hidden;
  background: #000;
}

.paragraph-text :deep(.video-block iframe) {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  border: none;
}

/* ── Markdown 元素样式 ── */
.paragraph-text :deep(h1) {
  font-size: 1.75em;
  font-weight: 700;
  margin: 1.2em 0 0.6em;
  line-height: 1.3;
  color: var(--text-primary);
}

.paragraph-text :deep(h2) {
  font-size: 1.45em;
  font-weight: 700;
  margin: 1.1em 0 0.5em;
  line-height: 1.35;
  color: var(--text-primary);
}

.paragraph-text :deep(h3) {
  font-size: 1.2em;
  font-weight: 600;
  margin: 1em 0 0.45em;
  line-height: 1.4;
  color: var(--text-primary);
}

.paragraph-text :deep(h4) {
  font-size: 1.05em;
  font-weight: 600;
  margin: 0.9em 0 0.4em;
  line-height: 1.45;
  color: var(--text-primary);
}

.paragraph-text :deep(p) {
  margin: 0 0 1em;
}

.paragraph-text :deep(p:last-child) {
  margin-bottom: 0;
}

.paragraph-text :deep(code) {
  font-family: var(--font-mono, 'Fira Code', 'Consolas', monospace);
  font-size: 0.9em;
  padding: 0.2em 0.4em;
  background: var(--surface-hover-color, rgba(128, 128, 128, 0.1));
  border-radius: 3px;
  word-break: break-word;
}

.paragraph-text :deep(pre) {
  background: var(--surface-hover-color, rgba(128, 128, 128, 0.08));
  border-radius: var(--radius-md);
  padding: 1em;
  margin: 0.8em 0;
  overflow-x: auto;
  line-height: 1.6;
}

.paragraph-text :deep(pre code) {
  background: none;
  padding: 0;
  font-size: 0.85em;
  color: inherit;
}

.paragraph-text :deep(ul) {
  margin: 0.5em 0;
  padding-left: 1.5em;
  list-style: disc;
}

.paragraph-text :deep(ol) {
  margin: 0.5em 0;
  padding-left: 1.5em;
  list-style: decimal;
}

.paragraph-text :deep(li) {
  margin: 0.25em 0;
}

.paragraph-text :deep(blockquote) {
  margin: 0.8em 0;
  padding: 0.5em 1em;
  border-left: 4px solid var(--primary-color, #667eea);
  background: var(--surface-hover-color, rgba(128, 128, 128, 0.05));
  border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
  color: var(--text-secondary);
  overflow: visible;
}

.paragraph-text :deep(blockquote p) {
  margin: 0.3em 0;
}

.paragraph-text :deep(blockquote p:last-child) {
  margin-bottom: 0;
}

.paragraph-text :deep(a) {
  color: var(--primary-color, #667eea);
  text-decoration: underline;
  text-underline-offset: 2px;
  transition: color var(--transition-fast);
}

.paragraph-text :deep(a:hover) {
  color: var(--primary-hover-color, #5a6fd6);
}

.paragraph-text :deep(hr) {
  border: none;
  border-top: 1px solid var(--border-color, rgba(128, 128, 128, 0.2));
  margin: 1.5em 0;
}

/* ── code 类型 ── */
.paragraph-code {
  background: var(--surface-hover-color, rgba(128, 128, 128, 0.08));
  border-radius: var(--radius-md);
  padding: 1em;
  margin: 0.8em 0;
  overflow-x: auto;
  line-height: 1.6;
  font-family: var(--font-mono, 'Fira Code', 'Consolas', monospace);
  font-size: 0.9em;
}

/* ── image 类型 ── */
.paragraph-image {
  margin: 1.5em 0;
  text-align: center;
}

.paragraph-image img {
  max-width: 100%;
  width: 100%;
  max-width: 720px;
  border-radius: var(--radius-md);
  display: block;
  margin: 0 auto;
}

.paragraph-image figcaption {
  font-size: 13px;
  color: var(--text-tertiary);
  margin-top: 6px;
  font-family: var(--font-sans);
}

/* ── quote 类型 ── */
.paragraph-quote {
  margin: 0.8em 0;
  padding: 0.5em 1em;
  border-left: 4px solid var(--primary-color, #667eea);
  background: var(--surface-hover-color, rgba(128, 128, 128, 0.05));
  border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
  color: var(--text-secondary);
  font-family: var(--font-serif);
  font-size: 16.5px;
  line-height: 2;
}

.paragraph-quote p {
  margin: 0.3em 0;
}

.paragraph-quote p:last-child {
  margin-bottom: 0;
}

/* ── heading 类型 ── */
.paragraph-heading {
  font-size: 1.2em;
  font-weight: 600;
  margin: 1em 0 0.45em;
  line-height: 1.4;
  color: var(--text-primary);
  font-family: var(--font-sans);
}
</style>
