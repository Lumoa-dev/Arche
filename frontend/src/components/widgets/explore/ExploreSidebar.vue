<script setup lang="ts">
/**
 * ExploreSidebar — 探索页筛选侧栏
 *
 * 标签/用户模式切换 + 可勾选标签/作者列表 + 激活的筛选 chips
 */
import { computed } from 'vue'
import { NIcon, NTag } from 'naive-ui'
import { PersonOutline, PricetagOutline } from '@vicons/ionicons5'

const props = withDefaults(
  defineProps<{
    filterMode?: 'tag' | 'author'
    selectedTags?: string[]
    selectedAuthors?: string[]
    allTags?: string[]
    allAuthors?: string[]
  }>(),
  {
    filterMode: 'tag',
    selectedTags: () => [],
    selectedAuthors: () => [],
    allTags: () => [],
    allAuthors: () => []
  }
)

const emit = defineEmits<{
  'update:filterMode': [mode: 'tag' | 'author']
  'update:selectedTags': [tags: string[]]
  'update:selectedAuthors': [authors: string[]]
}>()

type FilterChip = {
  type: '标签' | '用户'
  value: string
}

const activeCompoundFilters = computed<FilterChip[]>(() => [
  ...(props.selectedTags.length > 0
    ? props.selectedTags.map((value) => ({ type: '标签' as const, value }))
    : []),
  ...(props.selectedAuthors.length > 0
    ? props.selectedAuthors.map((value) => ({ type: '用户' as const, value }))
    : [])
])

function isOptionChecked(option: string) {
  if (props.filterMode === 'tag') {
    return option === '全部' ? props.selectedTags.length === 0 : props.selectedTags.includes(option)
  }
  return option === '全部作者'
    ? props.selectedAuthors.length === 0
    : props.selectedAuthors.includes(option)
}

function toggleOption(option: string) {
  if (props.filterMode === 'tag') {
    if (option === '全部') {
      emit('update:selectedTags', [])
      return
    }
    const next = props.selectedTags.includes(option)
      ? props.selectedTags.filter((t) => t !== option)
      : [...props.selectedTags, option]
    emit('update:selectedTags', next)
    return
  }
  if (option === '全部作者') {
    emit('update:selectedAuthors', [])
    return
  }
  const next = props.selectedAuthors.includes(option)
    ? props.selectedAuthors.filter((a) => a !== option)
    : [...props.selectedAuthors, option]
  emit('update:selectedAuthors', next)
}

function removeChip(chip: FilterChip) {
  if (chip.type === '标签') {
    emit(
      'update:selectedTags',
      props.selectedTags.filter((t) => t !== chip.value)
    )
  } else {
    emit(
      'update:selectedAuthors',
      props.selectedAuthors.filter((a) => a !== chip.value)
    )
  }
}

const tagThemeOverrides = {
  borderRadius: '8px',
  colorChecked: 'var(--primary-color)',
  colorCheckedHover: 'var(--primary-hover-color)',
  colorCheckedPressed: 'var(--primary-pressed-color)',
  textColorChecked: '#fff',
  border: 'none',
  padding: '0 14px',
  height: '30px',
  fontSize: '13px',
  color: 'var(--surface-color)',
  textColor: 'var(--text-primary)',
  colorCheckable: 'transparent',
  colorHoverCheckable: 'var(--surface-hover-color)'
}
</script>

<template>
  <aside class="explore-sidebar">
    <!-- 模式切换 -->
    <div class="filter-tabs">
      <button
        class="filter-tab"
        :class="{ active: filterMode === 'tag' }"
        type="button"
        @click="emit('update:filterMode', 'tag')"
      >
        <NIcon size="14" aria-hidden="true">
          <PricetagOutline />
        </NIcon>
        <span>标签</span>
      </button>
      <button
        class="filter-tab"
        :class="{ active: filterMode === 'author' }"
        type="button"
        @click="emit('update:filterMode', 'author')"
      >
        <NIcon size="14" aria-hidden="true">
          <PersonOutline />
        </NIcon>
        <span>用户</span>
      </button>
    </div>

    <!-- 标签/作者列表 -->
    <Transition name="tag-stack-panel" mode="out-in">
      <div :key="filterMode" class="tag-stack">
        <NTag
          v-for="option in filterMode === 'tag' ? allTags : allAuthors"
          :key="option"
          checkable
          :checked="isOptionChecked(option)"
          class="stack-tag"
          :theme-overrides="tagThemeOverrides"
          @update:checked="() => toggleOption(option)"
        >
          {{ option }}
        </NTag>
      </div>
    </Transition>

    <!-- 激活的筛选 chips -->
    <div v-if="activeCompoundFilters.length > 0" class="filter-bar">
      <TransitionGroup name="filter-chip" tag="div" class="filter-chip-list">
        <button
          v-for="chip in activeCompoundFilters"
          :key="`${chip.type}-${chip.value}`"
          type="button"
          class="filter-chip"
          @click="removeChip(chip)"
        >
          <span class="chip-label">{{ chip.type }}</span>
          <span class="chip-value">{{ chip.value }}</span>
          <span class="chip-close" aria-hidden="true">×</span>
        </button>
      </TransitionGroup>
    </div>
  </aside>
</template>

<style scoped>
.explore-sidebar {
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  align-items: center;
  gap: var(--spacing-md);
  width: 100%;
  max-width: 320px;
  min-height: 360px;
  padding: var(--spacing-md);
  box-sizing: border-box;
  position: sticky;
  top: 87px;
  align-self: start;
  max-height: calc(100vh - 87px);
  overflow-y: auto;
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
}

.filter-tabs {
  display: flex;
  gap: 4px;
  width: 100%;
  background: var(--bg-inset-color);
  border-radius: var(--radius-md);
  padding: 3px;
  border: 1px solid var(--border-color);
  box-sizing: border-box;
}

.filter-tab {
  flex: 1;
  height: 32px;
  border: 0;
  border-radius: calc(var(--radius-md) - 2px);
  background: transparent;
  color: var(--text-tertiary);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  font-size: 13px;
  cursor: pointer;
  transition: all var(--transition-fast);
  font-family: var(--font-sans);
}

.filter-tab.active {
  background: var(--surface-color);
  color: var(--text-primary);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
}

.tag-stack {
  display: flex;
  flex-wrap: wrap;
  flex: 1;
  gap: 8px;
  overflow-y: auto;
  min-height: 0;
  width: 100%;
  margin: 0;
  padding: var(--spacing-md);
  box-sizing: border-box;
  align-content: flex-start;
  background: var(--bg-inset-color);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-color);
}

.stack-tag {
  margin: 0;
  transition: transform var(--transition-fast);
}

.stack-tag:hover {
  transform: translateY(-1px);
}

.tag-stack-panel-enter-active,
.tag-stack-panel-leave-active {
  transition:
    opacity var(--transition-normal),
    transform var(--transition-normal);
}

.tag-stack-panel-enter-from,
.tag-stack-panel-leave-to {
  opacity: 0;
  transform: translateY(4px);
}

.filter-bar {
  width: 100%;
}

.filter-chip-list {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.filter-chip {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 4px 10px 4px 12px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-full);
  background: var(--surface-color);
  cursor: pointer;
  font-family: var(--font-sans);
  font-size: 12px;
  transition: all var(--transition-fast);
}

.filter-chip:hover {
  background: var(--surface-strong-color);
  border-color: var(--text-tertiary);
}

.chip-label {
  color: var(--text-tertiary);
}

.chip-value {
  color: var(--text-primary);
  font-weight: var(--font-weight-medium);
}

.chip-close {
  color: var(--text-tertiary);
  font-size: 14px;
  line-height: 1;
  margin-left: 2px;
}

.filter-chip:hover .chip-close {
  color: var(--error-color);
}

.filter-chip-enter-active,
.filter-chip-leave-active {
  transition: all var(--transition-normal);
}

.filter-chip-enter-from,
.filter-chip-leave-to {
  opacity: 0;
  transform: translateY(4px) scale(0.96);
}

.filter-chip-move {
  transition: transform var(--transition-normal);
}
</style>
