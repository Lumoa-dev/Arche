<script setup lang="ts">
/**
 * EditorToolbar — Word 风格工具栏
 *
 * 宏观：一行横排，整体居中。
 * 历史|字体|段落|样式|插入 居中块，文档组推至右侧。
 *
 * 两行组内部用 CSS Grid 严格对齐。
 * TODO: 与 TipTap editor 实例联动实时反映格式状态
 */
import ArHBox from '@/components/ui/ArHBox.vue'
import ArButton from '@/components/ui/ArButton.vue'
import type { ParagraphType } from '@/components/logic/useParagraphEditor'
import {
  ListOutline,
  ColorPaletteOutline,
  ImageOutline,
  VideocamOutline,
  CodeSlashOutline,
  RemoveOutline,
  SaveOutline,
  SendOutline,
  ChatbubbleOutline
} from '@/icons'

defineProps<{
  hasActiveEditor: boolean
  saving: boolean
  isEdit: boolean
  execCommand: (cmd: string) => void
}>()

const emit = defineEmits<{
  insert: [type: ParagraphType]
  insertSeparator: []
  toggleCover: []
  saveDraft: []
  publish: []
  cancel: []
}>()
</script>

<template>
  <div class="toolbar-outer">
    <div class="toolbar-rail">
      <!-- ═══ 居中块 ═══ -->
      <div class="toolbar-left" />

      <div class="toolbar-center">

        <!-- 字体（两行 grid：上 4 下 2） -->
        <div class="group group--double group-font">
          <div class="group-row">
            <ArButton size="xs" type="ghost" icon title="加粗" :disabled="!hasActiveEditor" @click="execCommand('toggleBold')">
              <template #icon>
                <svg
                  width="16"
                  height="16"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2.2"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                >
                  <path d="M6 4h6a4 4 0 1 1 0 8H6z" />
                  <path d="M6 12h7a4 4 0 1 1 0 8H6z" />
                </svg>
              </template>
            </ArButton>
            <ArButton size="xs" type="ghost" icon title="斜体" :disabled="!hasActiveEditor" @click="execCommand('toggleItalic')">
              <template #icon>
                <svg
                  width="16"
                  height="16"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2.2"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                >
                  <line x1="17" y1="6" x2="10" y2="18" />
                  <line x1="19" y1="6" x2="14" y2="6" />
                  <line x1="10" y1="18" x2="5" y2="18" />
                </svg>
              </template>
            </ArButton>
            <ArButton size="xs" type="ghost" icon title="下划线" :disabled="!hasActiveEditor" @click="execCommand('toggleUnderline')">
              <template #icon>
                <svg
                  width="16"
                  height="16"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2.2"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                >
                  <path d="M6 4v6a6 6 0 0 0 12 0V4" />
                  <line x1="4" y1="20" x2="20" y2="20" />
                </svg>
              </template>
            </ArButton>
            <ArButton size="xs" type="ghost" icon title="删除线" :disabled="!hasActiveEditor" @click="execCommand('toggleStrike')">
              <template #icon>
                <svg
                  width="16"
                  height="16"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2.2"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                >
                  <path d="M6 5c0-1 .7-2 2-2h8c1.3 0 2 1 2 2" />
                  <path d="M18 12H6" />
                  <path d="M16 19c0 1-.7 2-2 2H9c-1.3 0-2-1-2-2" />
                </svg>
              </template>
            </ArButton>
          </div>
          <div class="group-row">
            <!-- 行内代码 -->
            <ArButton size="xs" type="ghost" icon title="行内代码" :disabled="!hasActiveEditor" @click="execCommand('toggleCode')">
              <template #icon>
                <svg
                  width="16"
                  height="16"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                >
                  <polyline points="16 18 22 12 16 6" />
                  <polyline points="8 6 2 12 8 18" />
                </svg>
              </template>
            </ArButton>
            <!-- 文字颜色 -->
            <ArButton size="xs" type="ghost" icon title="文字颜色" :disabled="!hasActiveEditor" @click="execCommand('setColor')">
              <template #icon><ColorPaletteOutline /></template>
            </ArButton>
          </div>
          <span class="group__label">字体</span>
        </div>

        <div class="group-divider" />

        <!-- 段落（两行 grid：上 3 下 4） -->
        <div class="group group--double group-paragraph">
          <div class="group-row">
            <ArButton size="xs" type="ghost" icon title="左对齐" :disabled="!hasActiveEditor" @click="execCommand('setTextAlignLeft')">
              <template #icon>
                <svg
                  width="16"
                  height="16"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                  stroke-linecap="round"
                >
                  <line x1="3" y1="6" x2="21" y2="6" />
                  <line x1="3" y1="10" x2="15" y2="10" />
                  <line x1="3" y1="14" x2="19" y2="14" />
                  <line x1="3" y1="18" x2="13" y2="18" />
                </svg>
              </template>
            </ArButton>
            <ArButton size="xs" type="ghost" icon title="居中" :disabled="!hasActiveEditor" @click="execCommand('setTextAlignCenter')">
              <template #icon>
                <svg
                  width="16"
                  height="16"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                  stroke-linecap="round"
                >
                  <line x1="3" y1="6" x2="21" y2="6" />
                  <line x1="5" y1="10" x2="19" y2="10" />
                  <line x1="3" y1="14" x2="21" y2="14" />
                  <line x1="6" y1="18" x2="18" y2="18" />
                </svg>
              </template>
            </ArButton>
            <ArButton size="xs" type="ghost" icon title="右对齐" :disabled="!hasActiveEditor" @click="execCommand('setTextAlignRight')">
              <template #icon>
                <svg
                  width="16"
                  height="16"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                  stroke-linecap="round"
                >
                  <line x1="3" y1="6" x2="21" y2="6" />
                  <line x1="9" y1="10" x2="21" y2="10" />
                  <line x1="5" y1="14" x2="21" y2="14" />
                  <line x1="11" y1="18" x2="21" y2="18" />
                </svg>
              </template>
            </ArButton>
          </div>
          <div class="group-row">
            <ArButton size="xs" type="ghost" icon title="引用" :disabled="!hasActiveEditor" @click="execCommand('toggleBlockquote')">
              <template #icon><ChatbubbleOutline /></template>
            </ArButton>
            <ArButton size="xs" type="ghost" icon title="无序列表" :disabled="!hasActiveEditor" @click="execCommand('toggleBulletList')">
              <template #icon><ListOutline /></template>
            </ArButton>
            <ArButton size="xs" type="ghost" icon title="有序列表" :disabled="!hasActiveEditor" @click="execCommand('toggleOrderedList')">
              <template #icon>
                <svg
                  width="16"
                  height="16"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                  stroke-linecap="round"
                >
                  <line x1="9" y1="6" x2="21" y2="6" />
                  <line x1="9" y1="12" x2="21" y2="12" />
                  <line x1="9" y1="18" x2="21" y2="18" />
                  <text x="3" y="9" font-size="8" font-weight="bold" fill="currentColor">1</text>
                  <text x="3" y="15" font-size="8" font-weight="bold" fill="currentColor">2</text>
                  <text x="3" y="21" font-size="8" font-weight="bold" fill="currentColor">3</text>
                </svg>
              </template>
            </ArButton>
            <ArButton
              size="xs"
              type="ghost"
              icon
              title="分隔线"
              :disabled="!hasActiveEditor"
              @click="emit('insertSeparator')"
            >
              <template #icon><RemoveOutline /></template>
            </ArButton>
          </div>
          <span class="group__label">段落</span>
        </div>

        <div class="group-divider" />

        <!-- 样式（两行 grid：上 2 下 2） -->
        <div class="group group--double group-styles">
          <div class="group-row">
            <ArButton
              size="xs"
              type="ghost"
              title="标题 1"
              :disabled="!hasActiveEditor"
              @click="execCommand('toggleHeading1')"
              style="font-weight: 700; font-size: 11px; min-width: 26px; padding: 0 3px"
              >H1</ArButton
            >
            <ArButton
              size="xs"
              type="ghost"
              title="标题 2"
              :disabled="!hasActiveEditor"
              @click="execCommand('toggleHeading2')"
              style="font-weight: 600; font-size: 10px; min-width: 24px; padding: 0 2px"
              >H2</ArButton
            >
          </div>
          <div class="group-row">
            <ArButton
              size="xs"
              type="ghost"
              title="标题 3"
              :disabled="!hasActiveEditor"
              @click="execCommand('toggleHeading3')"
              style="font-weight: 500; font-size: 10px; min-width: 22px; padding: 0 2px"
              >H3</ArButton
            >
            <ArButton
              size="xs"
              type="ghost"
              title="标题 4"
              :disabled="!hasActiveEditor"
              @click="execCommand('toggleHeading4')"
              style="font-weight: 400; font-size: 9px; min-width: 22px; padding: 0 2px"
              >H4</ArButton
            >
          </div>
          <span class="group__label">样式</span>
        </div>

        <div class="group-divider" />

        <!-- 插入（左大竖按钮 + 右小图标） -->
        <div class="group group--single group-insert">
          <div class="insert-area">
            <!-- 大竖按钮（可拖动） -->
            <button
              class="insert-big"
              :disabled="!hasActiveEditor"
              title="插入段落（可拖动到编辑区）"
              @click="emit('insert', 'text')"
            >
              <span class="insert-big__text">插入</span>
              <span class="insert-big__dots">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                  <circle cx="7" cy="17" r="1.5" />
                  <circle cx="17" cy="17" r="1.5" />
                  <circle cx="7" cy="12" r="1.5" />
                  <circle cx="17" cy="12" r="1.5" />
                  <circle cx="7" cy="7" r="1.5" />
                  <circle cx="17" cy="7" r="1.5" />
                </svg>
              </span>
            </button>

            <!-- 右侧纯图标按钮列 -->
            <div class="insert-icons">
              <ArButton
                size="xs"
                type="ghost"
                icon
                title="插入图片"
                @click="emit('insert', 'image')"
              >
                <template #icon><ImageOutline /></template>
              </ArButton>
              <ArButton
                size="xs"
                type="ghost"
                icon
                title="插入视频"
                @click="emit('insert', 'video')"
              >
                <template #icon><VideocamOutline /></template>
              </ArButton>
              <ArButton
                size="xs"
                type="ghost"
                icon
                title="插入代码块"
                @click="emit('insert', 'code')"
              >
                <template #icon><CodeSlashOutline /></template>
              </ArButton>
              <ArButton
                size="xs"
                type="ghost"
                icon
                title="插入分隔符"
                @click="emit('insertSeparator')"
              >
                <template #icon><RemoveOutline /></template>
              </ArButton>
              <!-- 设置封面 -->
              <ArButton
                size="xs"
                type="ghost"
                @click="emit('toggleCover')"
                title="设置封面"
                style="gap: 2px"
              >
                <template #icon>
                  <svg
                    width="14"
                    height="14"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="2.2"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                  >
                    <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
                    <circle cx="8.5" cy="8.5" r="1.5" />
                    <polyline points="21 15 16 10 5 21" />
                  </svg>
                </template>
                封面
              </ArButton>
            </div>
          </div>
          <span class="group__label">插入</span>
        </div>
      </div>

      <!-- ═══ 右侧：文档 ═══ -->
      <div class="toolbar-right">
        <div class="group group--single group-doc">
          <ArHBox gap="6px" align="center">
            <ArButton
              size="sm"
              type="secondary"
              :loading="saving"
              @click="emit('saveDraft')"
              title="存草稿"
              style="gap: 2px"
            >
              <template #icon><SaveOutline /></template>
              存稿
            </ArButton>
            <ArButton
              size="sm"
              type="primary"
              :loading="saving"
              @click="emit('publish')"
              title="发布"
              style="gap: 2px"
            >
              <template #icon><SendOutline /></template>
              {{ isEdit ? '保存' : '发送' }}
            </ArButton>
            <ArButton size="sm" type="ghost" @click="emit('cancel')" title="取消"> 取消 </ArButton>
          </ArHBox>
          <span class="group__label">文档</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* ════════════════════════════════════════
   工具栏 — 一行居中的 Word 风格
   历史 | 字体 | 段落 | 样式 | 插入 → 居中
   文档 → 右侧
   ════════════════════════════════════════ */

.toolbar-outer {
  position: sticky;
  top: 0;
  z-index: 10;
  background: var(--surface-color);
  border-bottom: 1px solid var(--border-color);
  user-select: none;
  height: 64px;
}

.toolbar-rail {
  display: flex;
  align-items: center;
  height: 100%;
  padding: 0 16px;
}

/* 三栏布局：左中右，中栏真正居中 */
.toolbar-left {
  flex: 1;
  min-width: 0;
}

.toolbar-center {
  display: flex;
  align-items: center;
  gap: 0;
  flex: 0 0 auto;
}

.toolbar-right {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  min-width: 0;
}

/* ── 组公共 ── */
.group {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.group__label {
  font-size: 9px;
  line-height: 1;
  color: var(--text-tertiary);
  letter-spacing: 0.04em;
  user-select: none;
  white-space: nowrap;
  margin-top: 1px;
}

.group--single {
  padding: 0 12px;
}

/* ── 两行组 ── */
.group--double {
  gap: 0;
  padding: 2px 12px;
}

.group-row {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 3px;
  min-height: 24px;
}

/* ── 组分隔线 ── */
.group-divider {
  width: 1px;
  align-self: center;
  height: 32px;
  background: var(--divider-color);
  flex-shrink: 0;
}

/* ════════════════════════════════════════
   插入组 — 左大竖按钮 + 右图标列
   ════════════════════════════════════════ */
.insert-area {
  display: flex;
  align-items: center;
  gap: 4px;
}

/* 大竖按钮 */
.insert-big {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  width: 36px;
  height: 44px;
  background: transparent;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  cursor: pointer;
  color: var(--text-primary);
  transition: background var(--transition-fast);
  flex-shrink: 0;
}

.insert-big:hover {
  background: var(--surface-strong-color);
}

.insert-big:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.insert-big__text {
  font-size: 12px;
  line-height: 1;
  font-family: var(--font-sans);
}

.insert-big__dots {
  display: flex;
  align-items: center;
  color: var(--text-tertiary);
  line-height: 1;
}

/* 右侧图标列 */
.insert-icons {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 2px;
}
</style>
