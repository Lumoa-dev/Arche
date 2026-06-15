<script setup lang="ts">
/**
 * AuthorBar — 文章作者信息栏（三行布局）
 * Row 1: [头像] 作者名  +  点赞/收藏/分享
 * Row 2: @username · 日期
 * Row 3: 统计数据（交互后显示）
 */
import { computed } from 'vue'
import LikeButton from '@/components/widgets/common/LikeButton.vue'
import FavoriteButton from '@/components/widgets/common/FavoriteButton.vue'
import ShareButton from '@/components/widgets/common/ShareButton.vue'

const props = withDefaults(
  defineProps<{
    postId: string
    authorUsername?: string
    createdAt?: string
    liked?: boolean
    favorited?: boolean
    likeCount?: number
    canInteract?: boolean
  }>(),
  {
    authorUsername: '',
    createdAt: '',
    liked: false,
    favorited: false,
    likeCount: 0,
    canInteract: false
  }
)

const emit = defineEmits<{
  toggleLike: []
  toggleFavorite: []
  share: []
}>()

const authorInitial = computed(() => {
  return (props.authorUsername || '?').charAt(0).toUpperCase()
})

const displayDate = computed(() => {
  if (!props.createdAt) return ''
  const date = new Date(props.createdAt)
  const now = new Date()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  if (date.getFullYear() === now.getFullYear()) {
    return `${month}-${day}`
  }
  return `${date.getFullYear()}-${month}-${day}`
})
</script>

<template>
  <div class="author-bar">
    <!-- Row 1: 头像 + 作者名 + 操作按钮 -->
    <div class="author-bar__row author-bar__main">
      <div class="author-bar__info">
        <div class="author-bar__avatar">{{ authorInitial }}</div>
        <span class="author-bar__name">{{ authorUsername || '匿名' }}</span>
      </div>
      <div class="author-bar__actions">
        <LikeButton
          :count="liked ? likeCount : 0"
          :active="liked"
          :disabled="!canInteract"
          @toggle="emit('toggleLike')"
        />
        <FavoriteButton
          :active="favorited"
          :disabled="!canInteract"
          @toggle="emit('toggleFavorite')"
        />
        <ShareButton :disabled="!canInteract" />
      </div>
    </div>

    <!-- Row 2: @username · 日期 -->
    <div class="author-bar__row author-bar__meta">
      <span class="author-bar__username">@{{ authorUsername || 'anonymous' }}</span>
      <span class="author-bar__dot">·</span>
      <span class="author-bar__date">{{ displayDate }}</span>
    </div>

    <!-- Row 3: 统计数据（交互后显示） -->
    <div v-if="liked || favorited" class="author-bar__row author-bar__stats">
      <span v-if="liked && likeCount > 0" class="stat">{{ likeCount }} 次点赞</span>
      <span v-if="favorited" class="stat">已收藏</span>
    </div>
  </div>
</template>

<style scoped>
.author-bar {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: var(--spacing-md) 0;
  border-bottom: 1px solid var(--divider-color);
  margin-bottom: var(--spacing-lg);
}

.author-bar__row {
  display: flex;
  align-items: center;
}

.author-bar__main {
  justify-content: space-between;
}

.author-bar__info {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.author-bar__avatar {
  width: 32px;
  height: 32px;
  border-radius: var(--radius-full);
  background: var(--primary-light-color);
  color: var(--primary-color);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: var(--font-weight-semibold);
  user-select: none;
  flex-shrink: 0;
}

.author-bar__name {
  font-size: 14px;
  font-weight: var(--font-weight-medium);
  color: var(--text-primary);
}

.author-bar__actions {
  display: flex;
  align-items: center;
  gap: 2px;
}

.author-bar__meta {
  gap: var(--spacing-xs);
  font-size: 12px;
  color: var(--text-tertiary);
  padding-left: calc(32px + var(--spacing-sm)); /* 与头像对齐 */
}

.author-bar__dot {
  opacity: 0.4;
}

.author-bar__stats {
  gap: var(--spacing-md);
  font-size: 12px;
  color: var(--text-tertiary);
  padding-left: calc(32px + var(--spacing-sm));
}

.stat {
  font-variant-numeric: tabular-nums;
}
</style>
