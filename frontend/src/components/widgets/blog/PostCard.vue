<script setup lang="ts">
import { computed } from 'vue'
import { NIcon } from 'naive-ui'
import { EyeOutline, HeartOutline, BookmarkOutline, ChatbubbleOutline } from '@vicons/ionicons5'
import ArTag from '@/components/ui/ArTag.vue'
import { getCoverGradient } from '@/lib/utils/cover'
import type { BlogPost } from '@/components/logic/api'

type PostCardMode = 'showcase' | 'media' | 'feed' | 'stack' | 'cover' | 'compact' | 'dense'

const props = withDefaults(
  defineProps<{
    post: BlogPost
    mode?: PostCardMode
    /** showcase 模式下是否显示文字叠加层 */
    showOverlay?: boolean
    /** media 模式下是否显示底部分享/点赞栏 */
    showActions?: boolean
    /** stack 模式下左侧标签内容（作者名等） */
    label?: string
    /** cover 模式下观看进度 (0-100) */
    metaProgress?: number
    /** cover 模式下阅读时长文字 */
    metaDuration?: string
  }>(),
  {
    mode: 'media',
    showOverlay: true,
    showActions: false
  }
)

const emit = defineEmits<{
  open: [post: BlogPost]
}>()

const TAG_COLORS = ['red', 'blue', 'yellow', 'green', 'default'] as const

const authorName = computed(() => props.post.author_username || '匿名')
const authorDisplay = computed(() => `@ ${authorName.value}`)
const dateStr = computed(() => props.post.created_at?.slice(0, 10) || '-')

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

const excerpt = computed(() => {
  const text = props.post.introduction?.abstract ?? ''
  return text.slice(0, 120)
})

// compact/dense 模式用更短的摘要
const shortExcerpt = computed(() => {
  const text = props.post.introduction?.abstract ?? ''
  return text.slice(0, 50)
})

const displayTags = computed(() => (props.post.tags || []).slice(0, 3))

/** 是否有任何封面（真实封面或自动生成封面） */
const hasAnyCover = computed(() => !!(props.post.cover_url || props.post.auto_cover_url))
/** 当前可用的封面 URL（真实封面优先，否则用自动生成的） */
const anyCoverUrl = computed(() => props.post.cover_url || props.post.auto_cover_url || '')
/** compact 模式是否是有真实封面（非自动生成）的帖子 */
const hasRealCover = computed(() => !!props.post.cover_url)
/** compact 模式使用的封面 URL（真实封面优先，否则用自动生成的） */
const displayCoverUrl = computed(() => props.post.cover_url || props.post.auto_cover_url || '')

function tagColor(index: number) {
  return TAG_COLORS[index % TAG_COLORS.length]!
}

/** 日期格式化：今年 → "04-01"，往年 → "2025-04-01" */
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

const displayDate = computed(() => formatDate(props.post.created_at || ''))

function handleClick() {
  emit('open', props.post)
}
</script>

<template>
  <article :class="['post-card', `post-card--${mode}`]" @click="handleClick">
    <!-- ═══ showcase: 全出血封面 + 叠加文字 ═══ -->
    <template v-if="mode === 'showcase'">
      <div class="sc-cover" :style="coverStyle">
        <div class="sc-shine" />
      </div>
      <div v-if="showOverlay" class="sc-overlay">
        <div class="sc-overlay-body">
          <span class="sc-author">{{ authorName }}</span>
          <h3 class="sc-title">{{ post.title }}</h3>
        </div>
      </div>
    </template>

    <!-- ═══ media: 封面(<img> 自然宽高比) + 内容卡片 ═══ -->
    <template v-if="mode === 'media'">
      <!-- 有封面（用户上传或自动生成）→ <img> 保留原始比例 -->
      <div v-if="hasAnyCover" class="md-cover">
        <img :src="anyCoverUrl" alt="" class="md-cover-img" loading="lazy" />
      </div>
      <!-- 无封面 → 渐变色占位，固定比例 -->
      <div v-else class="md-cover md-cover--fallback" :style="coverStyle" />

      <div class="md-body">
        <h4 class="md-title">{{ post.title }}</h4>
        <p class="md-excerpt">{{ excerpt }}</p>
        <div class="md-footer">
          <div class="md-meta">
            <span class="md-author">{{ authorName }}</span>
            <span class="md-sep">·</span>
            <span class="md-date">{{ dateStr }}</span>
          </div>
          <div v-if="displayTags.length > 0" class="md-tags">
            <ArTag
              v-for="(tag, i) in displayTags"
              :key="tag"
              :color="tagColor(i)"
              size="sm"
              type="light"
            >
              {{ tag }}
            </ArTag>
          </div>
        </div>
      </div>

      <footer v-if="showActions" class="md-actions">
        <span class="action-item">
          <NIcon size="14"><HeartOutline /></NIcon>
          <em>{{ post.likes || 0 }}</em>
        </span>
        <span class="action-item">
          <NIcon size="14"><BookmarkOutline /></NIcon>
        </span>
        <span class="action-item">
          <NIcon size="14"><ChatbubbleOutline /></NIcon>
        </span>
      </footer>
    </template>

    <!-- ═══ feed: 紧凑型（极小缩略图 / 纯文字） ═══ -->
    <template v-if="mode === 'feed'">
      <div v-if="hasAnyCover" class="fd-thumb" :style="coverStyle" />
      <div class="fd-body">
        <h4 class="fd-title">{{ post.title }}</h4>
        <div class="fd-meta">
          <span>{{ authorName }}</span>
          <span class="fd-sep">·</span>
          <span>{{ dateStr }}</span>
        </div>
      </div>
    </template>

    <!-- ═══ stack: 紧凑堆叠卡（标签 + 贴面封面 + 标题底栏） ═══ -->
    <template v-if="mode === 'stack'">
      <div class="sk-body">
        <div class="sk-label">
          <span class="sk-label-text">{{ label || authorName }}</span>
        </div>
        <div class="sk-cover" :style="coverStyle">
          <div class="sk-cover-shine" />
        </div>
      </div>
      <div class="sk-title-bar">
        <span class="sk-title">{{ post.title }}</span>
      </div>
    </template>

    <!-- ═══ cover: 全封面 + 信息浮层 ═══ -->
    <template v-if="mode === 'cover'">
      <div class="cv-card" :style="coverStyle">
        <!-- 顶部：左→右渐变，标题 + @作者 -->
        <div class="cv-top-overlay">
          <span class="cv-title">{{ post.title }}</span>
          <span class="cv-author">@{{ authorName }}</span>
        </div>
        <!-- 底部：进度 + 时长 -->
        <div class="cv-bottom-overlay">
          <span v-if="metaProgress != null" class="cv-progress"> 已读 {{ metaProgress }}% </span>
          <span v-if="metaDuration" class="cv-duration">{{ metaDuration }}</span>
        </div>
      </div>
    </template>

    <!-- ═══ compact: 封面+内容分区卡片（首页用） ═══ -->
    <!-- 有封面 → 放大封面 + 压缩文字；无封面 → 自动文字封面 + 文字优待 -->
    <template v-if="mode === 'compact'">
      <!-- 封面区 -->
      <div class="cp-cover-wrap">
        <div v-if="displayCoverUrl" class="cp-cover">
          <img
            :src="displayCoverUrl"
            alt=""
            class="cp-cover-img"
            :class="{ 'cp-cover-img--auto': !hasRealCover }"
            loading="lazy"
          />
        </div>
        <!-- 统计数据（右下角） -->
        <div class="cp-cover-stats">
          <span class="cp-stat-item">
            <NIcon size="12"><EyeOutline /></NIcon>
            {{ post.views ?? 0 }}
          </span>
          <span class="cp-stat-item">
            <NIcon size="12"><HeartOutline /></NIcon>
            {{ post.likes ?? 0 }}
          </span>
        </div>
      </div>

      <!-- 内容区：有封面 → 文字少；无封面 → 文字多 -->
      <div :class="['cp-body', { 'cp-body--text-priority': !hasRealCover }]">
        <h4 :class="['cp-title', { 'cp-title--compact': hasRealCover }]">{{ post.title }}</h4>
        <p v-if="hasRealCover && shortExcerpt" class="cp-excerpt cp-excerpt--compact">
          {{ shortExcerpt }}
        </p>
        <p v-if="!hasRealCover" class="cp-excerpt cp-excerpt--expanded">{{ excerpt }}</p>
        <div v-if="displayTags.length > 0" class="cp-tags">
          <ArTag
            v-for="(tag, i) in displayTags"
            :key="tag"
            :color="tagColor(i)"
            size="sm"
            type="light"
          >
            {{ tag }}
          </ArTag>
        </div>
        <div class="cp-footer">
          <span class="cp-badge">博主</span>
          <span class="cp-author">{{ authorDisplay }}</span>
          <span class="cp-sep">·</span>
          <span class="cp-time">{{ displayDate }}</span>
        </div>
      </div>
    </template>

    <!-- ═══ dense: 高文字密度卡片（探索页用） ═══ -->
    <template v-if="mode === 'dense'">
      <div class="dn-body">
        <h4 class="dn-title">{{ post.title }}</h4>
        <p v-if="shortExcerpt" class="dn-excerpt">{{ shortExcerpt }}</p>
        <div class="dn-meta">
          <span class="dn-author">
            <span class="dn-badge">博主</span>
            {{ authorDisplay }}
          </span>
          <span class="dn-sep">·</span>
          <span class="dn-time">{{ displayDate }}</span>
          <span class="dn-sep">·</span>
          <span class="dn-likes">♥ {{ post.likes || 0 }}</span>
        </div>
        <div v-if="displayTags.length > 0" class="dn-tags">
          <ArTag
            v-for="(tag, i) in displayTags"
            :key="tag"
            :color="tagColor(i)"
            size="sm"
            type="light"
          >
            {{ tag }}
          </ArTag>
        </div>
      </div>
    </template>
  </article>
</template>

<style scoped>
/* ── 通用 ── */
.post-card {
  cursor: pointer;
  font-family: var(--font-sans);
  transition:
    transform var(--ease-out-smooth),
    box-shadow var(--ease-out-smooth);
  touch-action: manipulation;
}
.post-card:focus-visible {
  outline: 2px solid var(--primary-color);
  outline-offset: 2px;
}

/* ══════════ SHOWCASE ══════════ */
.post-card--showcase {
  position: relative;
  width: 100%;
  height: 100%;
  overflow: hidden;
  border-radius: inherit;
}

.sc-cover {
  position: absolute;
  inset: 0;
  background-size: cover;
  background-position: center;
  border-radius: inherit;
}

.sc-shine {
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

.sc-overlay {
  position: absolute;
  inset: 0;
  background: linear-gradient(180deg, transparent 50%, rgba(26, 24, 23, 0.75) 100%);
  display: flex;
  align-items: flex-end;
  padding: var(--spacing-lg);
  pointer-events: none;
}

.sc-overlay-body {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.sc-author {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.75);
  font-weight: var(--font-weight-medium);
}

.sc-title {
  margin: 0;
  font-size: 18px;
  font-weight: var(--font-weight-semibold);
  color: #fff;
  line-height: 1.35;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-shadow: 0 1px 4px rgba(0, 0, 0, 0.3);
}

/* ══════════ MEDIA ══════════ */
.post-card--media {
  display: flex;
  flex-direction: column;
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  overflow: hidden;
  box-shadow: var(--shadow-sm);
}

.post-card--media:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

.md-cover {
  width: 100%;
  overflow: hidden;
  line-height: 0;
}

.md-cover-img {
  width: 100%;
  height: auto;
  display: block;
  animation: md-img-in 0.4s var(--ease-out-smooth) both;
}

@keyframes md-img-in {
  from {
    opacity: 0;
    transform: scale(1.02);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

.md-cover--fallback {
  aspect-ratio: 16 / 9;
  background-size: cover;
  background-position: center;
}

.md-body {
  padding: var(--spacing-md);
  display: flex;
  flex-direction: column;
  gap: 6px;
  flex: 1;
}

/* 底部区域：作者信息 + 标签，自然推到底部 */
.md-footer {
  margin-top: auto;
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding-top: 4px;
}

.md-meta {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: var(--text-quaternary);
}

.md-author {
  color: var(--text-secondary);
  font-weight: var(--font-weight-medium);
}

.md-date {
  color: var(--text-tertiary);
}

.md-sep {
  color: var(--text-quaternary, rgba(26, 24, 23, 0.18));
}

.md-title {
  margin: 0;
  font-size: 16px;
  font-weight: var(--font-weight-semibold);
  line-height: 1.4;
  color: var(--text-primary);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.md-excerpt {
  margin: 0;
  font-size: 13px;
  line-height: 1.55;
  color: var(--text-secondary);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.md-tags {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.md-actions {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  padding: var(--spacing-sm) var(--spacing-md);
  border-top: 1px solid var(--border-color);
}

.action-item {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: var(--text-tertiary);
  font-variant-numeric: tabular-nums;
}

.action-item em {
  font-style: normal;
}

/* ══════════ FEED ══════════ */
.post-card--feed {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  padding: var(--spacing-sm) var(--spacing-md);
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-color);
  background: var(--surface-color);
}

.post-card--feed:hover {
  border-color: var(--primary-color);
  background: var(--primary-light-color);
}

.fd-thumb {
  width: 40px;
  height: 40px;
  flex-shrink: 0;
  border-radius: var(--radius-sm);
  overflow: hidden;
  background-size: cover;
  background-position: center;
}

.fd-body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.fd-title {
  margin: 0;
  font-size: 14px;
  font-weight: var(--font-weight-medium);
  line-height: 1.4;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.fd-meta {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: var(--text-tertiary);
}

.fd-sep {
  color: var(--text-quaternary, rgba(26, 24, 23, 0.18));
}

/* ══════════ STACK ══════════ */
.post-card--stack {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100%;
  border-radius: var(--radius-lg);
  overflow: hidden;
  background: var(--surface-strong-color);
}

.sk-body {
  flex: 1;
  display: flex;
  min-height: 0;
}

/* ── 左侧标签（竖排文字，宽可通过 --sk-label-w 覆写） ── */
.sk-label {
  width: var(--sk-label-w, 38px);
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  writing-mode: vertical-rl;
  text-orientation: upright;
  background: var(--surface-inset-color);
}

.sk-label-text {
  font-size: 11px;
  font-weight: var(--font-weight-medium);
  color: var(--text-secondary);
  letter-spacing: 2px;
}

/* ── 封面（"贴上去"的层次感） ── */
.sk-cover {
  flex: 1;
  background-size: cover;
  background-position: center;
  position: relative;
  /* 右边上下圆角与卡片对齐 */
  border-top-right-radius: inherit;
  border-bottom-right-radius: inherit;
  /* 左边上下独立小圆角 */
  border-top-left-radius: 5px;
  border-bottom-left-radius: 5px;
  /* 阴影产生"照片贴在表面"的深度感 */
  box-shadow:
    -1px 0 6px rgba(26, 24, 23, 0.06),
    2px 2px 8px rgba(26, 24, 23, 0.1);
}

.sk-cover-shine {
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.06) 0%, transparent 50%);
  pointer-events: none;
}

/* ── 底部标题栏（紧凑贴合） ── */
.sk-title-bar {
  padding: var(--sk-title-pad, 8px 10px);
  background: var(--surface-color);
}

.sk-title {
  font-size: var(--sk-title-size, 12px);
  font-weight: var(--font-weight-semibold);
  color: var(--text-primary);
  line-height: 1.35;
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
  letter-spacing: -0.01em;
}

/* 深色模式适配 */
:global(.dark) .sk-label {
  background: rgba(42, 39, 36, 0.72);
}

:global(.dark) .sk-cover {
  box-shadow:
    -1px 0 6px rgba(0, 0, 0, 0.15),
    2px 2px 8px rgba(0, 0, 0, 0.2);
}

:global(.dark) .sk-title-bar {
  background: rgba(26, 24, 23, 0.88);
}

/* ══════════ COVER ══════════ */
.post-card--cover {
  width: 100%;
  height: 100%;
  border-radius: inherit;
  overflow: hidden;
}

.cv-card {
  width: 100%;
  height: 100%;
  background-size: cover;
  background-position: center;
  position: relative;
}

/* ── 顶部 overlay：左→右渐隐 ── */
.cv-top-overlay {
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

.cv-title {
  font-size: 13px;
  font-weight: var(--font-weight-semibold);
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

.cv-author {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.88);
  white-space: nowrap;
  flex-shrink: 0;
  text-shadow: 0 1px 3px rgba(0, 0, 0, 0.3);
}

/* ── 底部 overlay：下→上渐隐 ── */
.cv-bottom-overlay {
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

.cv-progress {
  font-size: 11px;
  font-weight: var(--font-weight-medium);
  color: #fff;
  text-shadow: 0 1px 3px rgba(0, 0, 0, 0.4);
  font-variant-numeric: tabular-nums;
}

.cv-duration {
  font-size: 10px;
  color: rgba(255, 255, 255, 0.7);
  text-shadow: 0 1px 3px rgba(0, 0, 0, 0.3);
}

/* 深色模式 */
:global(.dark) .cv-top-overlay {
  background: linear-gradient(
    to right,
    rgba(0, 0, 0, 0.55) 0%,
    rgba(0, 0, 0, 0.2) 55%,
    transparent 100%
  );
}

:global(.dark) .cv-bottom-overlay {
  background: linear-gradient(to top, rgba(0, 0, 0, 0.6) 0%, transparent 100%);
}

/* ══════════ COMPACT (封面+内容分区卡片) ══════════ */
.post-card--compact {
  display: flex;
  flex-direction: column;
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  overflow: hidden;
  box-shadow: var(--shadow-sm);
  transition:
    transform 0.2s var(--ease-out-smooth),
    box-shadow 0.2s var(--ease-out-smooth);
}

.post-card--compact:hover {
  transform: translateY(-1px);
  box-shadow: var(--shadow-md);
}

/* ── 封面区 ── */
.cp-cover-wrap {
  position: relative;
  line-height: 0;
}

.cp-cover {
  width: 100%;
  overflow: hidden;
}

/* 有封面：大幅展示，自然比例，更大上限 */
.cp-cover-img {
  width: 100%;
  height: auto;
  display: block;
  max-height: 260px;
  object-fit: cover;
}

/* 自动生成文字封面：固定比例，小尺寸展示 */
.cp-cover-img--auto {
  max-height: 170px;
  aspect-ratio: 16 / 9;
  object-fit: cover;
}

/* 统计数据（右下角毛玻璃 pill） */
.cp-cover-stats {
  position: absolute;
  bottom: 6px;
  left: 6px;
  display: flex;
  align-items: center;
  gap: 8px;
  pointer-events: none;
  z-index: 1;
}

.cp-stat-item {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: 11px;
  font-weight: var(--font-weight-semibold);
  color: #fff;
  font-variant-numeric: tabular-nums;
  text-shadow: 0 1px 3px rgba(0, 0, 0, 0.5);
}

/* ── 内容区 ── */
.cp-body {
  padding: var(--spacing-sm) var(--spacing-md);
  display: flex;
  flex-direction: column;
  gap: 6px;
  flex: 1;
}

/* 无封面时文字区获得更多空间，内容更舒展 */
.cp-body--text-priority {
  padding: var(--spacing-md) var(--spacing-md);
  gap: 8px;
}

.cp-title {
  margin: 0;
  font-size: 14px;
  font-weight: var(--font-weight-semibold);
  line-height: 1.45;
  color: var(--text-primary);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* 有封面时标题只显示 1 行 */
.cp-title--compact {
  -webkit-line-clamp: 1;
}

.cp-excerpt {
  margin: 0;
  font-size: 12px;
  line-height: 1.5;
  color: var(--text-tertiary);
  display: -webkit-box;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* 有封面时正文只显示 1 行 */
.cp-excerpt--compact {
  -webkit-line-clamp: 1;
}

/* 无封面时正文显示 3 行，文字优待 */
.cp-excerpt--expanded {
  -webkit-line-clamp: 4;
  font-size: 13px;
  line-height: 1.55;
}

.cp-tags {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}

.cp-footer {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  line-height: 18px;
  color: var(--text-tertiary);
  margin-top: auto;
  padding-top: 6px;
  border-top: 1px solid var(--border-color);
}

.cp-badge {
  font-size: 11px;
  font-weight: var(--font-weight-semibold);
  color: var(--primary-color);
  line-height: 18px;
}

.cp-author {
  color: var(--text-secondary);
  font-weight: var(--font-weight-medium);
  font-size: 12px;
  letter-spacing: 0.01em;
}

.cp-time {
  color: var(--text-quaternary);
}

.cp-sep {
  color: var(--text-quaternary, rgba(26, 24, 23, 0.18));
}

/* ══════════ DENSE (高文字密度) ══════════ */
.post-card--dense {
  display: flex;
  flex-direction: column;
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  overflow: hidden;
  box-shadow: var(--shadow-sm);
  transition:
    transform 0.2s var(--ease-out-smooth),
    box-shadow 0.2s var(--ease-out-smooth);
}

.post-card--dense:hover {
  transform: translateY(-1px);
  box-shadow: var(--shadow-md);
}

.dn-body {
  padding: var(--spacing-md);
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.dn-title {
  margin: 0;
  font-size: 15px;
  font-weight: var(--font-weight-semibold);
  line-height: 1.4;
  color: var(--text-primary);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.dn-excerpt {
  margin: 0;
  font-size: 13px;
  line-height: 1.5;
  color: var(--text-secondary);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.dn-meta {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  line-height: 18px;
  color: var(--text-tertiary);
  flex-wrap: wrap;
}

.dn-author {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: var(--text-secondary);
  font-weight: var(--font-weight-medium);
}

.dn-badge {
  font-size: 11px;
  font-weight: var(--font-weight-semibold);
  line-height: 18px;
  color: var(--primary-color);
}

.dn-time {
  color: var(--text-quaternary);
}

.dn-likes {
  color: var(--text-tertiary);
}

.dn-sep {
  color: var(--text-quaternary, rgba(26, 24, 23, 0.18));
}

.dn-tags {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
  margin-top: 2px;
}
</style>
