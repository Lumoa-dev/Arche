<script setup lang="ts">
/**
 * PostCardForCover — 全封面 + 信息浮层卡片
 * 适合 WatchHistoryStack 等需要封面为主体的场景
 */
import { computed } from 'vue'
import type { BlogPost } from '@/components/logic/api'

const props = withDefaults(
  defineProps<{
    post: BlogPost
    metaProgress?: number
    metaDuration?: string
  }>(),
  {}
)

const emit = defineEmits<{
  open: [post: BlogPost]
}>()

const authorName = computed(() => props.post.author_username || '匿名')

const coverStyle = computed(() => {
  const url = props.post.cover_url || props.post.auto_cover_url
  if (url) {
    return {
      backgroundImage: `url(${url})`,
      backgroundSize: 'cover' as const,
      backgroundPosition: 'center' as const
    }
  }
  return { background: getCoverGradient(props.post) }
})

function getCoverGradient(post: BlogPost): string {
  const gradients = [
    'linear-gradient(135deg, #f2dfc7, #dcbca0)',
    'linear-gradient(135deg, #d9c8b0, #9f8169)',
    'linear-gradient(135deg, #e8d7bf, #c0a688)',
    'linear-gradient(135deg, #d0c2b1, #8f7560)'
  ]
  let hash = 0
  for (let i = 0; i < (post.id || '').length; i++) {
    hash = (hash << 5) - hash + post.id.charCodeAt(i)
    hash |= 0
  }
  return gradients[Math.abs(hash) % gradients.length] || gradients[0]!
}
</script>

<template>
  <div class="cover-card" :style="coverStyle" @click="emit('open', post)">
    <div class="cover-top">
      <span class="cover-title">{{ post.title }}</span>
      <span class="cover-author">@{{ authorName }}</span>
    </div>
    <div class="cover-bottom">
      <span v-if="metaProgress != null" class="cover-progress">已读 {{ metaProgress }}%</span>
      <span v-if="metaDuration" class="cover-duration">{{ metaDuration }}</span>
    </div>
  </div>
</template>

<style scoped>
.cover-card {
  width: 100%;
  height: 100%;
  background-size: cover;
  background-position: center;
  position: relative;
}

/* 顶部 overlay：左→右渐隐 */
.cover-top {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  padding: 6px 10px;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 8px;
  background: linear-gradient(
    to right,
    rgba(26, 24, 23, 0.5) 0%,
    rgba(26, 24, 23, 0.18) 50%,
    transparent 100%
  );
  pointer-events: none;
  min-height: 32px;
}
.cover-title {
  font-size: 13px;
  font-weight: 600;
  color: #fff;
  line-height: 1.3;
  text-shadow: 0 1px 4px rgba(0, 0, 0, 0.35);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  max-width: 72%;
  flex-shrink: 1;
}
.cover-author {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.88);
  white-space: nowrap;
  flex-shrink: 0;
  text-shadow: 0 1px 3px rgba(0, 0, 0, 0.3);
}

/* 底部 overlay：下→上渐隐 */
.cover-bottom {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 7px 12px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: linear-gradient(to top, rgba(26, 24, 23, 0.55) 0%, transparent 100%);
  pointer-events: none;
  min-height: 32px;
}
.cover-progress {
  font-size: 11px;
  font-weight: 500;
  color: #fff;
  text-shadow: 0 1px 3px rgba(0, 0, 0, 0.4);
  font-variant-numeric: tabular-nums;
}
.cover-duration {
  font-size: 10px;
  color: rgba(255, 255, 255, 0.7);
  text-shadow: 0 1px 3px rgba(0, 0, 0, 0.3);
}
</style>
