<script setup lang="ts">
import ArTag from '@/components/ui/ArTag.vue'

const props = withDefaults(
  defineProps<{
    tags: string[]
    activeTag?: string
    clickable?: boolean
  }>(),
  {
    clickable: false
  }
)

const emit = defineEmits<{
  select: [tag: string]
}>()

const TAG_COLORS = ['default', 'red', 'blue', 'yellow', 'green'] as const

function getTagColor(tag: string): (typeof TAG_COLORS)[number] {
  const idx = props.tags.indexOf(tag)
  if (idx === -1) return 'default'
  return TAG_COLORS[idx % TAG_COLORS.length]!
}

function handleSelect(tag: string) {
  if (!props.clickable) return
  emit('select', tag)
}
</script>

<template>
  <div :class="['tag-list', { 'tag-list--clickable': clickable }]">
    <ArTag
      v-for="tag in tags"
      :key="tag"
      :color="getTagColor(tag)"
      :class="{ 'is-active': tag === activeTag }"
      size="sm"
      type="light"
      @click="handleSelect(tag)"
    >
      {{ tag }}
    </ArTag>
  </div>
</template>

<style scoped>
.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.tag-list--clickable .ar-tag {
  cursor: pointer;
  transition:
    transform var(--transition-fast),
    box-shadow var(--transition-fast),
    opacity var(--transition-fast);
}

.tag-list--clickable .ar-tag:hover {
  transform: translateY(-1px);
  box-shadow: var(--shadow-sm);
}

.tag-list--clickable .ar-tag:active {
  transform: translateY(0);
}

.tag-list .ar-tag.is-active {
  outline: 2px solid var(--primary-color);
  outline-offset: 1px;
}
</style>
