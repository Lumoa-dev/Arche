<script setup lang="ts">
/**
 * PostCardForCompact — 首页紧凑型卡片，支持可选封面 + 内容分区
 * 使用 ArCard 构建，根据是否有真实封面切换布局密度
 */
import { computed } from 'vue'
import ArCard from '@/components/ui/ArCard.vue'
import ArTag from '@/components/ui/ArTag.vue'
import type { BlogPost } from '@/components/logic/api'

const props = withDefaults(
  defineProps<{
    post: BlogPost
    /** 入场动画延迟（ms），用于 staggered 效果 */
    delay?: number
  }>(),
  { delay: 0 }
)

const emit = defineEmits<{
  open: [post: BlogPost]
}>()

const TAG_COLORS = ['red', 'blue', 'yellow', 'green', 'default'] as const

const hasRealCover = computed(() => !!props.post.cover_url)
const displayCoverUrl = computed(() => props.post.cover_url || props.post.auto_cover_url || '')

/** 有真实封面时用短摘要，无封面时用长摘要 */
const excerptText = computed(() => {
  const text = props.post.introduction?.abstract ?? ''
  if (hasRealCover.value) return text.slice(0, 50)
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
  <ArCard
    variant="elevated"
    :padding="hasRealCover ? 'sm' : 'md'"
    hoverable
    class="card-in"
    :style="{ animationDelay: `${delay}ms` }"
    @click="emit('open', post)"
  >
    <!-- 封面区：仅在有封面 URL 时渲染 -->
    <template v-if="displayCoverUrl" #cover>
      <div style="position: relative; line-height: 0">
        <img
          :src="displayCoverUrl"
          alt=""
          style="width: 100%; display: block; max-height: 260px; object-fit: cover"
        />
        <!-- 统计浮层 -->
        <div
          style="position: absolute; bottom: 6px; left: 6px; display: flex; gap: 8px; z-index: 1"
        >
          <span
            style="
              display: inline-flex;
              align-items: center;
              gap: 3px;
              font-size: 11px;
              font-weight: 600;
              color: #fff;
              text-shadow: 0 1px 3px rgba(0, 0, 0, 0.5);
            "
          >
            <svg
              width="12"
              height="12"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2.5"
            >
              <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
              <circle cx="12" cy="12" r="3" />
            </svg>
            {{ post.views ?? 0 }}
          </span>
          <span
            style="
              display: inline-flex;
              align-items: center;
              gap: 3px;
              font-size: 11px;
              font-weight: 600;
              color: #fff;
              text-shadow: 0 1px 3px rgba(0, 0, 0, 0.5);
            "
          >
            <svg
              width="12"
              height="12"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2.5"
            >
              <path
                d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1-1a5.5 5.5 0 0 0-7.8 7.8l1 1L12 21l7.8-7.8 1-1a5.5 5.5 0 0 0 0-7.8z"
              />
            </svg>
            {{ post.likes ?? 0 }}
          </span>
        </div>
      </div>
    </template>

    <!-- 内容区 -->
    <template #default>
      <!-- 有封面时标题最多 1 行，无封面时最多 2 行 -->
      <h4
        :style="{
          margin: 0,
          fontSize: '14px',
          fontWeight: 600,
          lineHeight: '1.45',
          color: 'var(--text-primary)',
          display: '-webkit-box',
          WebkitLineClamp: hasRealCover ? 1 : 2,
          WebkitBoxOrient: 'vertical',
          overflow: 'hidden'
        }"
      >
        {{ post.title }}
      </h4>
      <p
        v-if="excerptText"
        :style="{
          margin: hasRealCover ? '4px 0 0' : '4px 0 0',
          fontSize: hasRealCover ? '12px' : '13px',
          lineHeight: hasRealCover ? '1.5' : '1.55',
          color: 'var(--text-tertiary)',
          display: '-webkit-box',
          WebkitLineClamp: hasRealCover ? 1 : 3,
          WebkitBoxOrient: 'vertical',
          overflow: 'hidden'
        }"
      >
        {{ excerptText }}
      </p>
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

    <!-- 底栏 -->
    <template #footer>
      <span style="font-size: 11px; font-weight: 600; color: var(--primary-color)">博主</span>
      <span style="font-size: 12px; color: var(--text-secondary); font-weight: 500"
        >@ {{ authorName }}</span
      >
      <span style="color: var(--text-quaternary, rgba(26, 24, 23, 0.18))">·</span>
      <span style="font-size: 12px; color: var(--text-quaternary)">{{ displayDate }}</span>
    </template>
  </ArCard>
</template>

<style scoped>
.card-in {
  animation: card-in 0.5s var(--ease-out-smooth) both;
}

@keyframes card-in {
  from {
    opacity: 0;
    transform: translateY(12px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
