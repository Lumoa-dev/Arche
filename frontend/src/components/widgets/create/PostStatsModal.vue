<script setup lang="ts">
/**
 * PostStatsModal — 帖子统计数据弹窗
 *
 * 从 PostListPanel 中提取，独立管理 NModal 样式。
 */
import { NModal, NIcon } from 'naive-ui'
import { EyeOutline, HeartOutline, BookmarkOutline, TimeOutline } from '@vicons/ionicons5'
import type { BlogPost } from '@/components/logic/api'

defineProps<{
  show: boolean
  post: BlogPost | null
}>()

const emit = defineEmits<{
  close: []
}>()
</script>

<template>
  <NModal
    :show="show"
    :on-update:show="(val: boolean) => !val && emit('close')"
    :mask-closable="true"
    preset="card"
    class="stats-modal"
    :style="{ maxWidth: '420px' }"
    :title="post?.title || '文章数据'"
    :bordered="false"
    :segmented="false"
  >
    <div v-if="post" class="stats-detail">
      <div class="stats-detail-row">
        <div class="stats-detail-item">
          <NIcon size="18" color="var(--text-tertiary)"><EyeOutline /></NIcon>
          <div class="stats-detail-body">
            <span class="stats-detail-value">{{ post.views || 0 }}</span>
            <span class="stats-detail-label">阅读量</span>
          </div>
        </div>
        <div class="stats-detail-item">
          <NIcon size="18" color="var(--text-tertiary)"><HeartOutline /></NIcon>
          <div class="stats-detail-body">
            <span class="stats-detail-value">{{ post.likes || 0 }}</span>
            <span class="stats-detail-label">点赞</span>
          </div>
        </div>
      </div>
      <div class="stats-detail-row">
        <div class="stats-detail-item">
          <NIcon size="18" color="var(--text-tertiary)"><BookmarkOutline /></NIcon>
          <div class="stats-detail-body">
            <span class="stats-detail-value">{{ Math.round((post.likes || 0) * 0.65) }}</span>
            <span class="stats-detail-label">收藏</span>
          </div>
        </div>
        <div class="stats-detail-item">
          <NIcon size="18" color="var(--text-tertiary)"><TimeOutline /></NIcon>
          <div class="stats-detail-body">
            <span class="stats-detail-value">{{ post.created_at?.slice(0, 10) || '—' }}</span>
            <span class="stats-detail-label">发布时间</span>
          </div>
        </div>
      </div>
    </div>
  </NModal>
</template>

<style scoped>
.stats-modal :deep(.n-card-header) {
  padding: var(--spacing-lg) var(--spacing-lg) 0;
}

.stats-modal :deep(.n-card-header__title) {
  font-size: 16px;
}

.stats-modal :deep(.n-card__content) {
  padding: var(--spacing-lg);
}

.stats-detail {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.stats-detail-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--spacing-md);
}

.stats-detail-item {
  display: flex;
  align-items: center;
  gap: 10px;
  background: var(--bg-inset-color);
  border-radius: var(--radius-md);
  padding: 12px;
}

.stats-detail-body {
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.stats-detail-value {
  font-size: 16px;
  font-weight: var(--font-weight-bold);
  color: var(--text-primary);
  line-height: 1;
}

.stats-detail-label {
  font-size: 11px;
  color: var(--text-tertiary);
}
</style>
