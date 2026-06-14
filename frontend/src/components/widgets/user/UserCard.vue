<script setup lang="ts">
import { computed } from 'vue'
import ArCard from '@/components/ui/ArCard.vue'

interface UserInfo {
  username: string
  nickname?: string
  avatar?: string
  bio?: string
  created_at?: string
}

const props = withDefaults(
  defineProps<{
    user: UserInfo
    size?: 'sm' | 'md' | 'lg'
    showStats?: boolean
  }>(),
  {
    size: 'md',
    showStats: false
  }
)

const initials = computed(() => {
  const name = props.user.nickname || props.user.username
  return name.charAt(0).toUpperCase()
})

const avatarColors = [
  '#3a5a4a', // 黛青
  '#4a7c94', // 靛蓝
  '#c23a2b', // 朱红
  '#d4a017', // 藤黄
  '#4a7a5a' // 松绿
]

const avatarColor = computed(() => {
  let hash = 0
  for (let i = 0; i < props.user.username.length; i++) {
    hash = props.user.username.charCodeAt(i) + ((hash << 5) - hash)
  }
  return avatarColors[Math.abs(hash) % avatarColors.length]
})

const avatarSize = computed(() => {
  switch (props.size) {
    case 'sm':
      return 36
    case 'lg':
      return 72
    default:
      return 52
  }
})

const displayName = computed(() => props.user.nickname || props.user.username)

const joinDate = computed(() => {
  if (!props.user.created_at) return null
  try {
    const date = new Date(props.user.created_at)
    return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`
  } catch {
    return null
  }
})
</script>

<template>
  <ArCard
    class="user-card"
    :class="[`user-card--${size}`]"
    :padding="size === 'sm' ? 'sm' : 'md'"
    hoverable
  >
    <div class="user-card__inner">
      <!-- Avatar -->
      <div class="user-card__avatar-wrap">
        <img
          v-if="user.avatar"
          :src="user.avatar"
          :alt="user.username"
          class="user-card__avatar"
          :style="{ width: avatarSize + 'px', height: avatarSize + 'px' }"
        />
        <div
          v-else
          class="user-card__avatar user-card__avatar--fallback"
          :style="{
            width: avatarSize + 'px',
            height: avatarSize + 'px',
            background: avatarColor
          }"
        >
          {{ initials }}
        </div>
      </div>

      <!-- Info -->
      <div class="user-card__info">
        <div class="user-card__name-row">
          <span class="user-card__display-name">{{ displayName }}</span>
          <span v-if="user.nickname && user.nickname !== user.username" class="user-card__username">
            @{{ user.username }}
          </span>
        </div>
        <p v-if="user.bio" class="user-card__bio">{{ user.bio }}</p>
      </div>
    </div>

    <!-- Stats -->
    <div v-if="showStats" class="user-card__stats">
      <div class="user-card__stat-item">
        <span class="user-card__stat-value">{{ joinDate || '—' }}</span>
        <span class="user-card__stat-label">加入时间</span>
      </div>
    </div>
  </ArCard>
</template>

<style scoped>
.user-card {
  width: 100%;
}

.user-card__inner {
  display: flex;
  gap: var(--spacing-md);
  align-items: center;
}

.user-card--sm .user-card__inner {
  gap: var(--spacing-sm);
}

.user-card--lg .user-card__inner {
  gap: var(--spacing-lg);
}

/* ── Avatar ── */
.user-card__avatar {
  border-radius: var(--radius-full);
  object-fit: cover;
  flex-shrink: 0;
  border: 2px solid var(--border-color);
}

.user-card__avatar--fallback {
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-full);
  flex-shrink: 0;
  color: #fff;
  font-weight: var(--font-weight-semibold);
  font-size: 18px;
  line-height: 1;
  user-select: none;
}

.user-card--sm .user-card__avatar--fallback {
  font-size: 14px;
}

.user-card--lg .user-card__avatar--fallback {
  font-size: 26px;
}

/* ── Info ── */
.user-card__info {
  flex: 1;
  min-width: 0;
}

.user-card__name-row {
  display: flex;
  align-items: baseline;
  gap: var(--spacing-sm);
  flex-wrap: wrap;
}

.user-card__display-name {
  font-weight: var(--font-weight-semibold);
  color: var(--text-primary);
  line-height: var(--line-height-tight);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.user-card--sm .user-card__display-name {
  font-size: 14px;
}

.user-card--md .user-card__display-name {
  font-size: 16px;
}

.user-card--lg .user-card__display-name {
  font-size: 20px;
}

.user-card__username {
  font-size: 13px;
  color: var(--text-tertiary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.user-card--lg .user-card__username {
  font-size: 14px;
}

.user-card__bio {
  margin: var(--spacing-xs) 0 0;
  font-size: 13px;
  color: var(--text-tertiary);
  line-height: var(--line-height-normal);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.user-card--sm .user-card__bio {
  font-size: 12px;
  margin-top: 2px;
}

.user-card--lg .user-card__bio {
  font-size: 14px;
}

/* ── Stats ── */
.user-card__stats {
  display: flex;
  gap: var(--spacing-lg);
  padding-top: var(--spacing-md);
  margin-top: var(--spacing-md);
  border-top: 1px solid var(--border-color);
}

.user-card--sm .user-card__stats {
  padding-top: var(--spacing-sm);
  margin-top: var(--spacing-sm);
  gap: var(--spacing-md);
}

.user-card__stat-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.user-card__stat-value {
  font-size: 16px;
  font-weight: var(--font-weight-semibold);
  color: var(--text-primary);
  font-variant-numeric: tabular-nums;
}

.user-card--sm .user-card__stat-value {
  font-size: 14px;
}

.user-card--lg .user-card__stat-value {
  font-size: 18px;
}

.user-card__stat-label {
  font-size: 11px;
  color: var(--text-tertiary);
}
</style>
