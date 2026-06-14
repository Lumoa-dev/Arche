<script setup lang="ts">
/**
 * RichTextEditor.vue — 基于 TipTap 的富文本编辑器组件
 *
 * 功能：
 * - 工具栏：加粗 / 斜体 / 下划线 / 删除线 / 字体大小 / 段落格式 /
 *   文字颜色 / 行内代码 / Emoji 选择器 / 撤销 / 重做
 * - [#N] 图片占位符渲染（自定义 NodeView）
 * - v-model 双向绑定（modelValue → HTML）
 */

import { ref, watch, onMounted, onBeforeUnmount, computed, defineComponent, h } from 'vue'
import { useEditor, EditorContent, VueNodeViewRenderer, NodeViewWrapper } from '@tiptap/vue-3'
import { Node, Extension, InputRule } from '@tiptap/core'
import { StarterKit } from '@tiptap/starter-kit'
import { Underline } from '@tiptap/extension-underline'
import { TextStyle } from '@tiptap/extension-text-style'
import { Color } from '@tiptap/extension-color'
import { TextAlign } from '@tiptap/extension-text-align'

// ── Props & Emits ──

const props = withDefaults(
  defineProps<{
    modelValue?: string
    placeholder?: string
  }>(),
  {
    modelValue: '',
    placeholder: '开始写下你的想法……'
  }
)

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

// ── 状态 ──

const isFocused = ref(false)
const showEmojiPicker = ref(false)
const showFontSizeDropdown = ref(false)
const showFormatDropdown = ref(false)
const showColorPicker = ref(false)

const emojiPickerRef = ref<HTMLElement | null>(null)
const fontSizeDropdownRef = ref<HTMLElement | null>(null)
const formatDropdownRef = ref<HTMLElement | null>(null)
const colorPickerRef = ref<HTMLElement | null>(null)

// ── FontSize 扩展 ──
// 在 TextStyle 基础上增加 fontSize 属性

function parseFontSize(el: HTMLElement) {
  const val = el.style.fontSize
  return val ? val.replace(/['"]+/g, '') : null
}

function renderFontSize(attrs: Record<string, unknown>) {
  if (!attrs.fontSize) return {}
  return { style: `font-size: ${attrs.fontSize}` }
}

const FontSize = Extension.create({
  name: 'fontSize',

  addGlobalAttributes() {
    return [
      {
        types: ['textStyle'],
        attributes: {
          fontSize: {
            default: null,
            parseHTML: parseFontSize,
            renderHTML: renderFontSize
          }
        }
      }
    ]
  },

  addCommands() {
    return {
      setFontSize:
        (fontSize: string) =>
        ({ chain }) => {
          return chain().setMark('textStyle', { fontSize }).run()
        },
      unsetFontSize:
        () =>
        ({ chain }) => {
          return chain().setMark('textStyle', { fontSize: null }).removeEmptyTextStyle().run()
        }
    }
  }
})

// ── [#N] 图片占位符 NodeView 组件 ──

const ImagePlaceholderNodeComponent = defineComponent({
  name: 'ImagePlaceholderNode',
  props: {
    node: { type: Object, required: true },
    editor: { type: Object, required: true },
    getPos: { type: Function, required: true },
    updateAttributes: { type: Function, required: true },
    deleteNode: { type: Function, required: true }
  },
  setup(props) {
    const index = computed(() => props.node.attrs.index as number)

    return () =>
      h(
        NodeViewWrapper,
        {
          class: 'image-placeholder-wrapper',
          as: 'span',
          'data-image-placeholder': '',
          'data-index': index.value
        },
        {
          default: () => [
            h('span', { class: 'placeholder-icon' }, '🖼'),
            h('span', { class: 'placeholder-label' }, `图片 #${index.value}`)
          ]
        }
      )
  }
})

// ── [#N] 图片占位符扩展 ──

function parsePlaceholderIndex(el: HTMLElement) {
  return Number(el.getAttribute('data-index')) || 1
}

function renderPlaceholderAttrs(attrs: Record<string, unknown>) {
  return { 'data-index': attrs.index }
}

const ImagePlaceholder = Node.create({
  name: 'imagePlaceholder',
  group: 'inline',
  inline: true,
  selectable: true,
  draggable: true,
  atom: true,

  addAttributes() {
    return {
      index: {
        default: 1,
        parseHTML: parsePlaceholderIndex,
        renderHTML: renderPlaceholderAttrs
      }
    }
  },

  parseHTML() {
    return [{ tag: 'span[data-image-placeholder]' }]
  },

  renderHTML({ node }) {
    return [
      'span',
      {
        'data-image-placeholder': '',
        'data-index': node.attrs.index,
        class: 'image-placeholder-render'
      },
      `[#${node.attrs.index}]`
    ]
  },

  addNodeView() {
    return VueNodeViewRenderer(ImagePlaceholderNodeComponent as any)
  },

  addInputRules() {
    function placeholderRuleHandler(
      this: any,
      props: { state: any; range: any; match: RegExpMatchArray }
    ) {
      const { state, range, match } = props
      const { tr } = state
      const start = range.from
      const end = range.to
      const index = parseInt(match[1]!, 10) || 1
      tr.replaceWith(start, end, this.type.create({ index }))
      return tr
    }

    return [
      new InputRule({
        find: /\[#(\d+)]\s?$/,
        handler: placeholderRuleHandler.bind(this)
      })
    ]
  }
})

// ── Emoji 列表 ──

const EMOJI_LIST = [
  '😀',
  '😂',
  '🤔',
  '😊',
  '👍',
  '🎉',
  '❤️',
  '🔥',
  '⭐',
  '👏',
  '💡',
  '📝',
  '🎨',
  '🚀',
  '💪',
  '🙏',
  '✨',
  '🥳',
  '🤩',
  '😎',
  '💯',
  '🎯',
  '🌈',
  '🌊'
]

// ── 字体大小选项 ──

const FONT_SIZE_OPTIONS = [
  { label: '默认', value: '' },
  { label: '大号', value: '18px' },
  { label: '小号', value: '13px' }
]

// ── 段落格式选项 ──

const FORMAT_OPTIONS = [
  { label: '正文', type: 'paragraph' },
  { label: '标题1', type: 'heading', level: 1 },
  { label: '标题2', type: 'heading', level: 2 },
  { label: '引用', type: 'blockquote' }
]

// ── 颜色选项 ──

const COLOR_OPTIONS = [
  { label: '黑色', value: '#000000' },
  { label: '红色', value: '#e74c3c' },
  { label: '蓝色', value: '#3498db' },
  { label: '绿色', value: '#27ae60' },
  { label: '橙色', value: '#e67e22' },
  { label: '紫色', value: '#9b59b6' },
  { label: '灰色', value: '#7f8c8d' }
]

// ── 当前字体大小显示 ──

const currentFontSizeLabel = computed(() => {
  if (!editor.value) return '默认'
  const attrs = editor.value.getAttributes('textStyle')
  const size = attrs.fontSize as string | undefined
  const found = FONT_SIZE_OPTIONS.find((o) => o.value === size)
  return found ? found.label : '默认'
})

// ── 当前段落格式显示 ──

const currentFormatLabel = computed(() => {
  if (!editor.value) return '正文'
  if (editor.value.isActive('heading', { level: 1 })) return '标题1'
  if (editor.value.isActive('heading', { level: 2 })) return '标题2'
  if (editor.value.isActive('blockquote')) return '引用'
  return '正文'
})

// ── 初始化编辑器 ──

const editor = useEditor({
  content: props.modelValue || '',
  extensions: [
    StarterKit.configure({
      heading: {
        levels: [1, 2]
      }
    }),
    Underline,
    TextStyle,
    Color,
    TextAlign.configure({
      types: ['heading', 'paragraph']
    }),
    FontSize,
    ImagePlaceholder
  ],
  onUpdate: handleEditorUpdate,
  onFocus: handleEditorFocus,
  onBlur: handleEditorBlur
})

function handleEditorUpdate({ editor: ed }: { editor: any }) {
  const html = ed.getHTML()
  emit('update:modelValue', html)
}

function handleEditorFocus() {
  isFocused.value = true
}

function handleEditorBlur() {
  isFocused.value = false
}

// ── 同步外部 modelValue ──

const isUpdatingFromExternal = ref(false)

watch(
  () => props.modelValue,
  (newVal) => {
    if (!editor.value) return
    if (isUpdatingFromExternal.value) return
    const currentHtml = editor.value.getHTML()
    if (newVal !== currentHtml) {
      editor.value.commands.setContent(newVal || '', {})
    }
  }
)

// ── 工具栏命令封装 ──

function execBold() {
  editor.value?.chain().focus().toggleBold().run()
}

function execItalic() {
  editor.value?.chain().focus().toggleItalic().run()
}

function execUnderline() {
  editor.value?.chain().focus().toggleUnderline().run()
}

function execStrike() {
  editor.value?.chain().focus().toggleStrike().run()
}

function execInlineCode() {
  editor.value?.chain().focus().toggleCode().run()
}

function execUndo() {
  editor.value?.chain().focus().undo().run()
}

function execRedo() {
  editor.value?.chain().focus().redo().run()
}

function execSetFontSize(size: string) {
  if (!editor.value) return
  if (size === '') {
    editor.value.chain().focus().unsetFontSize().run()
  } else {
    editor.value.chain().focus().setFontSize(size).run()
  }
  showFontSizeDropdown.value = false
}

function execSetFormat(type: string, level?: number) {
  if (!editor.value) return
  if (type === 'paragraph') {
    editor.value.chain().focus().setParagraph().run()
  } else if (type === 'heading' && level) {
    editor.value
      .chain()
      .focus()
      .toggleHeading({ level: level as 1 | 2 })
      .run()
  } else if (type === 'blockquote') {
    editor.value.chain().focus().toggleBlockquote().run()
  }
  showFormatDropdown.value = false
}

function execSetColor(color: string) {
  if (!editor.value) return
  editor.value.chain().focus().setColor(color).run()
  showColorPicker.value = false
}

function execUnsetColor() {
  if (!editor.value) return
  editor.value.chain().focus().unsetColor().run()
  showColorPicker.value = false
}

function execInsertEmoji(emoji: string) {
  if (!editor.value) return
  editor.value.chain().focus().insertContent(emoji).run()
  showEmojiPicker.value = false
}

// ── 点击外部关闭下拉面板 ──

function handleClickOutside(e: MouseEvent) {
  const target = e.target as globalThis.Node

  if (showEmojiPicker.value && emojiPickerRef.value && !emojiPickerRef.value.contains(target)) {
    showEmojiPicker.value = false
  }
  if (
    showFontSizeDropdown.value &&
    fontSizeDropdownRef.value &&
    !fontSizeDropdownRef.value.contains(target)
  ) {
    showFontSizeDropdown.value = false
  }
  if (
    showFormatDropdown.value &&
    formatDropdownRef.value &&
    !formatDropdownRef.value.contains(target)
  ) {
    showFormatDropdown.value = false
  }
  if (showColorPicker.value && colorPickerRef.value && !colorPickerRef.value.contains(target)) {
    showColorPicker.value = false
  }
}

// ── 生命周期 ──

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
})

onBeforeUnmount(() => {
  document.removeEventListener('click', handleClickOutside)
  editor.value?.destroy()
})
</script>

<template>
  <div class="rich-editor" :class="{ 'is-focused': isFocused }">
    <!-- 工具栏 -->
    <div class="editor-toolbar">
      <!-- 加粗 -->
      <button
        class="toolbar-btn"
        :class="{ 'is-active': editor?.isActive('bold') }"
        title="加粗"
        @click="execBold"
      >
        <svg viewBox="0 0 24 24" class="tb-icon" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M6 4h8a4 4 0 0 1 4 4 4 4 0 0 1-4 4H6z" />
          <path d="M6 12h9a4 4 0 0 1 4 4 4 4 0 0 1-4 4H6z" />
        </svg>
      </button>

      <!-- 斜体 -->
      <button
        class="toolbar-btn"
        :class="{ 'is-active': editor?.isActive('italic') }"
        title="斜体"
        @click="execItalic"
      >
        <svg viewBox="0 0 24 24" class="tb-icon" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="19" y1="4" x2="10" y2="4" />
          <line x1="14" y1="20" x2="5" y2="20" />
          <line x1="15" y1="4" x2="9" y2="20" />
        </svg>
      </button>

      <!-- 下划线 -->
      <button
        class="toolbar-btn"
        :class="{ 'is-active': editor?.isActive('underline') }"
        title="下划线"
        @click="execUnderline"
      >
        <svg viewBox="0 0 24 24" class="tb-icon" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M6 3v7a6 6 0 0 0 6 6 6 6 0 0 0 6-6V3" />
          <line x1="4" y1="21" x2="20" y2="21" />
        </svg>
      </button>

      <!-- 删除线 -->
      <button
        class="toolbar-btn"
        :class="{ 'is-active': editor?.isActive('strike') }"
        title="删除线"
        @click="execStrike"
      >
        <svg viewBox="0 0 24 24" class="tb-icon" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M16 4H9a3 3 0 0 0-3 3v0a3 3 0 0 0 3 3h6a3 3 0 0 1 3 3v0a3 3 0 0 1-3 3H8" />
          <line x1="3" y1="12" x2="21" y2="12" />
        </svg>
      </button>

      <!-- 分割符 -->
      <span class="tb-separator" />

      <!-- 字体大小 -->
      <div ref="fontSizeDropdownRef" class="tb-dropdown-wrap">
        <button
          class="toolbar-btn tb-dropdown-trigger"
          title="字体大小"
          @click.stop="showFontSizeDropdown = !showFontSizeDropdown"
        >
          <span class="tb-dropdown-label">{{ currentFontSizeLabel }}</span>
          <svg
            viewBox="0 0 24 24"
            class="tb-icon tb-icon-sm"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
          >
            <polyline points="6 9 12 15 18 9" />
          </svg>
        </button>
        <div v-if="showFontSizeDropdown" class="tb-dropdown-panel">
          <button
            v-for="opt in FONT_SIZE_OPTIONS"
            :key="opt.value"
            class="tb-dropdown-item"
            @click="execSetFontSize(opt.value)"
          >
            {{ opt.label }}
          </button>
        </div>
      </div>

      <!-- 段落格式 -->
      <div ref="formatDropdownRef" class="tb-dropdown-wrap">
        <button
          class="toolbar-btn tb-dropdown-trigger"
          title="段落格式"
          @click.stop="showFormatDropdown = !showFormatDropdown"
        >
          <span class="tb-dropdown-label">{{ currentFormatLabel }}</span>
          <svg
            viewBox="0 0 24 24"
            class="tb-icon tb-icon-sm"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
          >
            <polyline points="6 9 12 15 18 9" />
          </svg>
        </button>
        <div v-if="showFormatDropdown" class="tb-dropdown-panel">
          <button
            v-for="opt in FORMAT_OPTIONS"
            :key="opt.label"
            class="tb-dropdown-item"
            :class="{
              'is-active': editor?.isActive(opt.type as any, opt.level ? { level: opt.level } : {})
            }"
            @click="execSetFormat(opt.type, opt.level)"
          >
            {{ opt.label }}
          </button>
        </div>
      </div>

      <!-- 分割符 -->
      <span class="tb-separator" />

      <!-- 文字颜色 -->
      <div ref="colorPickerRef" class="tb-dropdown-wrap">
        <button
          class="toolbar-btn tb-dropdown-trigger"
          title="文字颜色"
          @click.stop="showColorPicker = !showColorPicker"
        >
          <svg
            viewBox="0 0 24 24"
            class="tb-icon"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
          >
            <circle cx="12" cy="12" r="5" />
            <line x1="12" y1="1" x2="12" y2="3" />
            <line x1="12" y1="21" x2="12" y2="23" />
            <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" />
            <line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
            <line x1="1" y1="12" x2="3" y2="12" />
            <line x1="21" y1="12" x2="23" y2="12" />
            <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" />
            <line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
          </svg>
        </button>
        <div v-if="showColorPicker" class="tb-dropdown-panel tb-color-panel">
          <div class="color-grid">
            <button
              v-for="c in COLOR_OPTIONS"
              :key="c.value"
              class="color-swatch"
              :class="{ 'is-active': editor?.isActive('textStyle', { color: c.value }) }"
              :style="{ backgroundColor: c.value }"
              :title="c.label"
              @click="execSetColor(c.value)"
            />
          </div>
          <button class="tb-dropdown-item color-clear" @click="execUnsetColor">清除颜色</button>
        </div>
      </div>

      <!-- 行内代码 -->
      <button
        class="toolbar-btn"
        :class="{ 'is-active': editor?.isActive('code') }"
        title="行内代码"
        @click="execInlineCode"
      >
        <svg viewBox="0 0 24 24" class="tb-icon" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="16 18 22 12 16 6" />
          <polyline points="8 6 2 12 8 18" />
        </svg>
      </button>

      <!-- 分割符 -->
      <span class="tb-separator" />

      <!-- Emoji 选择器 -->
      <div ref="emojiPickerRef" class="tb-dropdown-wrap">
        <button
          class="toolbar-btn"
          title="插入 Emoji"
          @click.stop="showEmojiPicker = !showEmojiPicker"
        >
          <svg
            viewBox="0 0 24 24"
            class="tb-icon"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
          >
            <circle cx="12" cy="12" r="10" />
            <path d="M8 14s1.5 2 4 2 4-2 4-2" />
            <line x1="9" y1="9" x2="9.01" y2="9" />
            <line x1="15" y1="9" x2="15.01" y2="9" />
          </svg>
        </button>
        <div v-if="showEmojiPicker" class="tb-dropdown-panel emoji-panel">
          <div class="emoji-grid">
            <button
              v-for="emoji in EMOJI_LIST"
              :key="emoji"
              class="emoji-item"
              :title="emoji"
              @click="execInsertEmoji(emoji)"
            >
              {{ emoji }}
            </button>
          </div>
        </div>
      </div>

      <!-- 右侧弹性空间 -->
      <span class="tb-spacer" />

      <!-- 撤销 -->
      <button class="toolbar-btn" title="撤销" @click="execUndo">
        <svg viewBox="0 0 24 24" class="tb-icon" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="1 4 1 10 7 10" />
          <path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10" />
        </svg>
      </button>

      <!-- 重做 -->
      <button class="toolbar-btn" title="重做" @click="execRedo">
        <svg viewBox="0 0 24 24" class="tb-icon" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="23 4 23 10 17 10" />
          <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10" />
        </svg>
      </button>
    </div>

    <!-- 编辑器内容区 -->
    <editor-content :editor="editor!" class="editor-content" />
  </div>
</template>

<style scoped>
/* ── 容器 ── */
.rich-editor {
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  background: var(--surface-color);
  overflow: hidden;
  transition:
    border-color var(--transition-fast),
    box-shadow var(--transition-fast);
}

.rich-editor.is-focused {
  border-color: var(--primary-color);
  box-shadow: 0 0 0 3px var(--primary-light-color);
}

/* ── 工具栏 ── */
.editor-toolbar {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 2px;
  padding: 6px 8px;
  border-bottom: 1px solid var(--border-color);
  background: var(--surface-strong-color);
  user-select: none;
}

/* ── 工具栏按钮 ── */
.toolbar-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  padding: 0;
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
  transition:
    background var(--transition-fast),
    color var(--transition-fast),
    border-color var(--transition-fast);
  outline: none;
}

.toolbar-btn:hover {
  background: var(--surface-inset-color);
  color: var(--text-primary);
}

.toolbar-btn:active {
  transform: scale(0.95);
}

.toolbar-btn.is-active {
  background: var(--primary-light-color);
  color: var(--primary-color);
  border-color: var(--primary-color);
}

/* ── 工具栏图标 ── */
.tb-icon {
  width: 18px;
  height: 18px;
  display: block;
}

.tb-icon-sm {
  width: 12px;
  height: 12px;
}

/* ── 分割符 ── */
.tb-separator {
  display: inline-block;
  width: 1px;
  height: 20px;
  margin: 0 4px;
  background: var(--divider-color);
  flex-shrink: 0;
}

/* ── 弹性空间 ── */
.tb-spacer {
  flex: 1;
}

/* ── 下拉按钮 ── */
.tb-dropdown-wrap {
  position: relative;
  display: inline-flex;
}

.tb-dropdown-trigger {
  width: auto;
  padding: 0 6px;
  gap: 2px;
  font-size: 13px;
  font-family: var(--font-sans);
}

.tb-dropdown-label {
  white-space: nowrap;
  font-size: 12px;
}

/* ── 下拉面板 ── */
.tb-dropdown-panel {
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  z-index: 100;
  min-width: 120px;
  padding: 4px;
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  box-shadow: var(--shadow-md);
  backdrop-filter: blur(12px);
}

/* ── 下拉项 ── */
.tb-dropdown-item {
  display: block;
  width: 100%;
  padding: 6px 12px;
  border: none;
  border-radius: 4px;
  background: transparent;
  color: var(--text-primary);
  font-size: 13px;
  font-family: var(--font-sans);
  text-align: left;
  cursor: pointer;
  transition: background var(--transition-fast);
  outline: none;
}

.tb-dropdown-item:hover {
  background: var(--primary-light-color);
}

.tb-dropdown-item.is-active {
  color: var(--primary-color);
  font-weight: var(--font-weight-semibold);
}

/* ── 颜色选择器 ── */
.tb-color-panel {
  min-width: 160px;
}

.color-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 4px;
  padding: 4px;
}

.color-swatch {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  border: 2px solid transparent;
  cursor: pointer;
  transition:
    transform var(--transition-fast),
    border-color var(--transition-fast);
  outline: none;
  padding: 0;
}

.color-swatch:hover {
  transform: scale(1.2);
}

.color-swatch.is-active {
  border-color: var(--text-primary);
  box-shadow: 0 0 0 2px var(--surface-color);
}

.color-clear {
  border-top: 1px solid var(--divider-color);
  margin-top: 4px;
  padding-top: 6px;
  text-align: center;
  font-size: 12px;
  color: var(--text-tertiary);
}

/* ── Emoji 面板 ── */
.emoji-panel {
  min-width: 200px;
}

.emoji-grid {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 2px;
  padding: 4px;
}

.emoji-item {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  padding: 0;
  border: none;
  border-radius: 4px;
  background: transparent;
  font-size: 20px;
  cursor: pointer;
  transition:
    background var(--transition-fast),
    transform var(--transition-fast);
  outline: none;
}

.emoji-item:hover {
  background: var(--primary-light-color);
  transform: scale(1.2);
}

/* ── 编辑器内容区 ── */
.editor-content {
  padding: var(--spacing-md);
  min-height: 300px;
  cursor: text;
  font-family: var(--font-sans);
  font-size: 15px;
  line-height: var(--line-height-relaxed);
  color: var(--text-primary);
}

/* ── TipTap 编辑器内部样式 ── */
.editor-content :deep(.ProseMirror) {
  min-height: 280px;
  outline: none;
  white-space: pre-wrap;
  word-wrap: break-word;
}

/* ── 占位符（空内容时） ── */
.editor-content :deep(.ProseMirror p.is-editor-empty:first-child::before) {
  content: attr(data-placeholder);
  float: left;
  color: var(--text-tertiary);
  pointer-events: none;
  height: 0;
}

/* ── 标题样式 ── */
.editor-content :deep(.ProseMirror h1) {
  font-size: 24px;
  font-weight: var(--font-weight-bold);
  margin: 0.6em 0 0.3em;
  color: var(--text-primary);
  line-height: var(--line-height-tight);
}

.editor-content :deep(.ProseMirror h2) {
  font-size: 20px;
  font-weight: var(--font-weight-semibold);
  margin: 0.5em 0 0.25em;
  color: var(--text-primary);
  line-height: var(--line-height-tight);
}

/* ── 引用样式 ── */
.editor-content :deep(.ProseMirror blockquote) {
  margin: 0.5em 0;
  padding: 0.5em 1em;
  border-left: 3px solid var(--primary-color);
  color: var(--text-secondary);
  background: var(--primary-light-color);
  border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
  font-style: italic;
}

/* ── 代码样式 ── */
.editor-content :deep(.ProseMirror code) {
  background: var(--surface-inset-color);
  color: var(--accent-cinnabar);
  padding: 2px 6px;
  border-radius: 4px;
  font-family: var(--font-mono);
  font-size: 0.9em;
}

/* ── 下划线 ── */
.editor-content :deep(.ProseMirror u) {
  text-decoration: underline;
}

/* ── 删除线 ── */
.editor-content :deep(.ProseMirror s) {
  text-decoration: line-through;
}

/* ── 段落间距 ── */
.editor-content :deep(.ProseMirror p) {
  margin: 0.25em 0;
}

/* ── [#N] 图片占位符 ── */
.editor-content :deep(.image-placeholder-wrapper) {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  margin: 0 2px;
  background: var(--surface-inset-color);
  border: 1px dashed var(--border-color);
  border-radius: var(--radius-sm);
  cursor: pointer;
  user-select: none;
  vertical-align: middle;
  transition:
    background var(--transition-fast),
    border-color var(--transition-fast);
}

.editor-content :deep(.image-placeholder-wrapper:hover) {
  background: var(--surface-strong-color);
  border-color: var(--text-tertiary);
}

.editor-content :deep(.placeholder-icon) {
  font-size: 16px;
  line-height: 1;
}

.editor-content :deep(.placeholder-label) {
  font-size: 13px;
  font-family: var(--font-mono);
  color: var(--text-secondary);
  font-weight: var(--font-weight-medium);
}

/* ── 选中状态 ── */
.editor-content :deep(.ProseMirror .image-placeholder-wrapper) {
  transition: box-shadow var(--transition-fast);
}

.editor-content :deep(.ProseMirror .image-placeholder-wrapper.selectedNode) {
  outline: 2px solid var(--primary-color);
  outline-offset: 2px;
  border-radius: var(--radius-sm);
}
</style>
