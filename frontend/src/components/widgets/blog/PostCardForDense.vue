<script setup lang="ts">
/**
 * PostCardForDense — 探索页高密度文字卡片
 * 纯文字展示，无封面区域
 */
import { computed } from 'vue'
import ArCard from '@/components/ui/ArCard.vue'
import ArTag from '@/components/ui/ArTag.vue'
import type { BlogPost } from '@/components/logic/api'

const props = defineProps<{
  post: BlogPost
}>()

const emit = defineEmits<{
  open: [post: BlogPost]
}>()

const TAG_COLORS = ['red', 'blue', 'yellow', 'green', 'default'] as const

const excerptText = computed(() => {
  const text = props.post.introduction?.abstract ?? ''
  return text.slice(0, 120)
})

const authorName = computed(() => props.post.author_username || '匿名')
const displayDate = computed(() => formatDate(props.post.created_at || ''))

function formatDate(dateStr: string): string {
  if (!dateStr || dateStr === '-') return '-'
  const date = new Date(dateStr)
  const now = new Date()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  if (date.getFullYear() === now.getFullYear()) {
    return `${month}-${day}`
  }
  return `${date.getFullYear()}-${month}-${day}`
}
</script>

<template>
  <ArCard variant="elevated" padding="md" hoverable @click="emit('open', post)">
    <template #default>
      <h4
        style="
          margin: 0;
          font-size: 15px;
          font-weight: 600;
          line-height: 1.4;
          color: var(--text-primary);
          display: -webkit-box;
          -webkit-line-clamp: 2;
          -webkit-box-orient: vertical;
          overflow: hidden;
        "
      >
        {{ post.title }}
      </h4>
      <p
        v-if="excerptText"
        style="
          margin: 4px 0 0;
          font-size: 13px;
          line-height: 1.5;
          color: var(--text-secondary);
          display: -webkit-box;
          -webkit-line-clamp: 2;
          -webkit-box-orient: vertical;
          overflow: hidden;
        "
      >
        {{ excerptText }}
      </p>
      <div
        style="
          display: flex;
          align-items: center;
          gap: 4px;
          font-size: 12px;
          color: var(--text-tertiary);
          flex-wrap: wrap;
          margin-top: 4px;
        "
      >
        <span
          style="
            display: inline-flex;
            align-items: center;
            gap: 4px;
            color: var(--text-secondary);
            font-weight: 500;
          "
        >
          <span
            style="
              font-size: 11px;
              font-weight: 600;
              line-height: 18px;
              color: var(--primary-color);
            "
            >博主</span
          >
          @ {{ authorName }}
        </span>
        <span style="color: var(--text-quaternary)">·</span>
        <span>{{ displayDate }}</span>
        <span style="color: var(--text-quaternary)">·</span>
        <span>&hearts; {{ post.likes || 0 }}</span>
      </div>
      <div
        v-if="post.tags?.length"
        style="display: flex; gap: 4px; flex-wrap: wrap; margin-top: 4px"
      >
        <ArTag
          v-for="(tag, i) in post.tags.slice(0, 3)"
          :key="tag"
          :color="TAG_COLORS[i % TAG_COLORS.length]"
          size="sm"
          type="light"
        >
          {{ tag }}
        </ArTag>
      </div>
    </template>
  </ArCard>
</template>
