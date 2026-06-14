<script setup lang="ts">
/**
 * CardToolbar — 段落卡片操作条（悬停浮现）
 *
 * 类型选择（紧凑标签） + 上移/下移/删除，全部右对齐。
 * 改成小标签触发菜单而非大下拉框，减少视觉重量。
 */
import { ref } from 'vue'
import ArHBox from '@/components/ui/ArHBox.vue'
import ArButton from '@/components/ui/ArButton.vue'
import type { ParagraphType } from '@/components/logic/useParagraphEditor'

defineProps<{
  type: ParagraphType
  canMoveUp: boolean
  canMoveDown: boolean
}>()

const emit = defineEmits<{
  'update:type': [type: ParagraphType]
  moveUp: []
  moveDown: []
  delete: []
}>()

const typeOptions: { label: string; value: ParagraphType }[] = [
  { label: '文本', value: 'text' },
  { label: '标题', value: 'heading' },
  { label: '图片', value: 'image' },
  { label: '视频', value: 'video' },
  { label: '代码', value: 'code' },
  { label: '表格', value: 'table' }
]

const showMenu = ref(false)

function selectType(type: ParagraphType) {
  emit('update:type', type)
  showMenu.value = false
}
</script>

<template>
  <ArHBox gap="4px" justify="flex-end" align="center">
    <!-- 类型切换标签 -->
    <div class="type-trigger" @click.stop="showMenu = !showMenu">
      <span class="type-trigger__label">{{ typeOptions.find(t => t.value === type)?.label || type }}</span>
      <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round">
        <polyline points="6 9 12 15 18 9" />
      </svg>
      <!-- 下拉菜单 -->
      <div v-if="showMenu" class="type-menu" @click.stop>
        <button
          v-for="opt in typeOptions"
          :key="opt.value"
          class="type-menu__item"
          :class="{ 'type-menu__item--active': opt.value === type }"
          @click="selectType(opt.value)"
        >
          {{ opt.label }}
        </button>
      </div>
    </div>

    <div class="ctrl-divider" />

    <ArButton size="sm" type="ghost" :disabled="!canMoveUp" @click="emit('moveUp')"> ↑ </ArButton>
    <ArButton size="sm" type="ghost" :disabled="!canMoveDown" @click="emit('moveDown')"> ↓ </ArButton>
    <ArButton size="sm" type="ghost" @click="emit('delete')"> × </ArButton>
  </ArHBox>
</template>

<style scoped>
.type-trigger {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 2px;
  padding: 2px 6px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: 11px;
  color: var(--text-tertiary);
  user-select: none;
  transition: background var(--transition-fast);
}

.type-trigger:hover {
  background: var(--surface-strong-color, rgba(128, 128, 128, 0.08));
  color: var(--text-secondary);
}

.type-trigger__label {
  white-space: nowrap;
}

.type-menu {
  position: absolute;
  top: 100%;
  right: 0;
  margin-top: 4px;
  min-width: 80px;
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  box-shadow: var(--card-shadow-glass);
  z-index: 20;
  overflow: hidden;
}

.type-menu__item {
  display: block;
  width: 100%;
  padding: 6px 12px;
  border: none;
  background: transparent;
  font-size: 12px;
  text-align: left;
  color: var(--text-primary);
  cursor: pointer;
  font-family: var(--font-sans);
  transition: background var(--transition-fast);
}

.type-menu__item:hover {
  background: var(--surface-hover-color);
}

.type-menu__item--active {
  color: var(--primary-color);
  font-weight: var(--font-weight-semibold);
}

.ctrl-divider {
  width: 1px;
  height: 16px;
  background: var(--divider-color);
  flex-shrink: 0;
}
</style>
