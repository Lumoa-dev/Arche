<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import ArTag from '@/components/ui/ArTag.vue'

// 标签颜色池（排除 red 和 primary，red 为特殊保留色）
const TAG_COLORS = ['blue', 'yellow', 'green', 'default'] as const
type TagColor = (typeof TAG_COLORS)[number]

const props = defineProps<{
  tags: string[]
  limit?: number
}>()

const emit = defineEmits<{
  select: [tag: string]
  create: []
}>()

// ── 2 行限制计算 ──
const TAG_UNIT = 78
const GAP = 6
const MAX_ROWS = 2

const containerRef = ref<HTMLElement>()
const maxVisible = ref(99)

function calcMaxVisible() {
  if (!containerRef.value) return
  const w = containerRef.value.clientWidth
  const perRow = Math.max(1, Math.floor((w + GAP) / (TAG_UNIT + GAP)))
  maxVisible.value = perRow * MAX_ROWS - 1
}

const renderedTags = computed(() => {
  const all = props.tags.slice(0, props.limit)
  return all.slice(0, Math.max(0, maxVisible.value))
})

// 给每个标签分配随机颜色（基于 index 确定性分配）
function tagColor(index: number): TagColor {
  return TAG_COLORS[index % TAG_COLORS.length]!
}

onMounted(() => {
  calcMaxVisible()
  const ro = new ResizeObserver(calcMaxVisible)
  if (containerRef.value) ro.observe(containerRef.value)
})
</script>

<template>
  <section class="trending-tags">
    <div class="tags-row">
      <!-- 左容器：常驻标签区 -->
      <div class="section-left">
        <div class="hot-text" @click="emit('select', '热门')">
          <span class="hot-line1">热门</span>
          <span class="hot-line2">推荐</span>
        </div>
      </div>

      <!-- 中容器：动态标签区 -->
      <div ref="containerRef" class="section-middle">
        <ArTag
          v-for="(tag, i) in renderedTags"
          :key="tag"
          :color="tagColor(i)"
          size="md"
          type="light"
          class="tag-btn"
          :title="tag.length > 4 ? tag : undefined"
          @click="emit('select', tag)"
        >
          {{ tag.slice(0, 4) }}
        </ArTag>
        <!-- 常驻「更多」标签 -->
        <ArTag
          size="md"
          color="primary"
          type="light"
          class="tag-btn more-btn"
          @click="emit('select', '__more__')"
        >
          更多
        </ArTag>
      </div>

      <!-- 右容器：活动区 -->
      <div class="section-right">
        <div class="create-cta" @click="emit('create')">
          <span class="cta-line1">分享你的</span>
          <span class="cta-line2">灵感</span>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.trending-tags {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-md) var(--spacing-lg);
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
}

.tags-row {
  display: flex;
  align-items: stretch;
  width: 100%;
  max-width: 860px;
  gap: var(--spacing-sm);
  min-height: 40px;
}

/* ── 左容器：常驻标签 ──
 * 规则：
 *   1. 只放按钮，不放 ArTag 等其他组件
 *   2. 不允许任何响应动画（hover/active 无变换）
 *   3. 形状必须是圆 pills（border-radius: 999px）
 *   4. 用 NIcon 图标代替 emoji 文字
 */
.section-left {
  display: flex;
  align-items: center;
  max-width: 180px;
  overflow-x: auto;
  scrollbar-width: none;
  gap: 8px;
  flex-shrink: 0;
}

.section-left::-webkit-scrollbar {
  display: none;
}

.hot-text {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 1px;
  cursor: pointer;
  flex-shrink: 0;
  padding: 2px 0;
  user-select: none;
}

.hot-line1 {
  font-size: 18px;
  font-weight: var(--font-weight-bold);
  color: var(--accent-red, #ef4444);
  line-height: 1.2;
  letter-spacing: 0.06em;
}

.hot-line2 {
  font-size: 10px;
  font-weight: var(--font-weight-medium);
  color: var(--text-quaternary);
  line-height: 1.3;
  letter-spacing: 0.04em;
}

/* 中区注释分隔 */
.section-middle {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-content: center;
  justify-content: center;
}

.tag-btn {
  cursor: pointer;
  transition: transform 0.15s ease;
}

.tag-btn:hover {
  transform: translateY(-1px);
}

.more-btn {
  font-weight: var(--font-weight-semibold);
}

/* ── 右容器：活动区 ── */
.section-right {
  display: flex;
  align-items: center;
  max-width: 140px;
  overflow-x: auto;
  scrollbar-width: none;
  gap: 8px;
  flex-shrink: 0;
}

.section-right::-webkit-scrollbar {
  display: none;
}

.create-cta {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 1px;
  cursor: pointer;
  flex-shrink: 0;
  padding: 2px 0;
  transition: opacity 0.2s ease;
  user-select: none;
}

.create-cta:hover {
  opacity: 0.8;
}

.cta-line1 {
  font-size: 11px;
  font-weight: var(--font-weight-medium);
  color: var(--text-tertiary);
  line-height: 1.3;
  letter-spacing: 0.08em;
}

.cta-line2 {
  font-size: 17px;
  font-weight: var(--font-weight-bold);
  color: var(--primary-color);
  line-height: 1.2;
  letter-spacing: 0.02em;
}

/* ── 响应式 ── */
@media (max-width: 640px) {
  .tags-row {
    flex-wrap: wrap;
    gap: var(--spacing-sm);
  }

  .section-left {
    max-width: none;
    width: 100%;
  }

  .hot-text {
    align-items: center;
  }

  .section-right {
    display: none;
  }
}
</style>
