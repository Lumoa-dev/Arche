<script setup lang="ts">
/**
 * PostCardForShowcase — 轮播全出血封面卡片
 * 使用背景图 + 文字叠加层，适合 HeroCarousel
 */
import { computed } from 'vue'
import type { BlogPost } from '@/components/logic/api'

const props = withDefaults(
  defineProps<{
    post: BlogPost
    showOverlay?: boolean
  }>(),
  { showOverlay: true }
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
  <div class="showcase-card" :style="coverStyle" @click="emit('open', post)">
    <div class="showcase-shine" />
    <div v-if="showOverlay" class="showcase-overlay">
      <div class="showcase-body">
        <span class="showcase-author">{{ authorName }}</span>
        <h3 class="showcase-title">{{ post.title }}</h3>
      </div>
    </div>
  </div>
</template>

<style scoped>
.showcase-card {
  position: relative;
  width: 100%;
  height: 100%;
  overflow: hidden;
  border-radius: inherit;
  background-size: cover;
  background-position: center;
  cursor: pointer;
}
.showcase-shine {
  position: absolute;
  inset: 0;
  background: linear-gradient(
    135deg,
    rgba(255, 255, 255, 0.08) 0%,
    transparent 40%,
    transparent 60%,
    rgba(255, 255, 255, 0.03) 100%
  );
  pointer-events: none;
}
.showcase-overlay {
  position: absolute;
  inset: 0;
  background: linear-gradient(180deg, transparent 50%, rgba(26, 24, 23, 0.75) 100%);
  display: flex;
  align-items: flex-end;
  padding: var(--spacing-lg);
  pointer-events: none;
}
.showcase-body {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.showcase-author {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.75);
  font-weight: 500;
}
.showcase-title {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #fff;
  line-height: 1.35;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-shadow: 0 1px 4px rgba(0, 0, 0, 0.3);
}
</style>
