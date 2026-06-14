<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NPagination, useMessage } from 'naive-ui'
import { getBlogPostsApi, type BlogPost } from '@/components/logic/api/blog'
import { withFallback, blogMockData } from '@/lib/services/mock'
import { useUserStore } from '@/lib/store/modules/user'
import { PostCard, HeroCarousel, TrendingTags, WatchHistoryStack } from '@/components/widgets'
import { ensurePostsCovers } from '@/components/logic/useCoverLazyGenerator'
import type { WatchHistoryItem } from '@/components/widgets/blog/WatchHistoryStack.vue'

const route = useRoute()
const router = useRouter()
const message = useMessage()
const userStore = useUserStore()

const loading = ref(false)
const posts = ref<BlogPost[]>([])
const hotPosts = ref<BlogPost[]>([])
const total = ref(0)
const page = ref(Number(route.query.page || 1))
const HOT_ROTATE_INTERVAL_MS = 12000

// ── Zone 2: trending tags from mock ──
const trendingTags = computed(() => blogMockData.tags.filter((t) => t !== '全部').slice(0, 20))

// ── Zone 3: watch history (only when logged in) ──
const historyItems = ref<WatchHistoryItem[]>([])

function buildHistoryItems(allPosts: BlogPost[]) {
  // dev 模式下免登录查看效果，production 仅登录态展示
  const showHistory = import.meta.env.DEV || userStore.isLoggedIn
  if (!showHistory || allPosts.length === 0) {
    historyItems.value = []
    return
  }
  const labels = ['刚刚', '5 分钟前', '1 小时前', '昨天', '3 天前']
  historyItems.value = allPosts.slice(0, 8).map((post, i) => ({
    post,
    progress: (Date.now() + i * 997) % 101,
    ...(labels[i % labels.length] ? { lastReadAt: labels[i % labels.length] } : {})
  }))
}

const fetchPosts = async () => {
  loading.value = true

  try {
    const [latestRes, hotRes] = await Promise.all([
      withFallback(
        () => getBlogPostsApi({ page: page.value, page_size: 12, sort_by: 'created_at' }),
        { list: [], total: 0, page: 0, page_size: 0 },
        { silent: true }
      ),
      withFallback(
        () => getBlogPostsApi({ page: 1, page_size: 6, sort_by: 'views' }),
        { list: [], total: 0, page: 0, page_size: 0 },
        { silent: true }
      )
    ])
    const latestList = latestRes.list || []
    const hotList = hotRes.list || []

    posts.value = latestList
    total.value = latestRes.total || 0
    buildHistoryItems(posts.value)
    if (hotList.length > 0) {
      hotPosts.value = hotList
    }
  } catch {
    posts.value = []
    hotPosts.value = []
  } finally {
    loading.value = false
    // 合并 latest 和 hot 列表，按 post.id 去重后统一触发封面生成
    const seen = new Set<string>()
    const allPosts = [...posts.value, ...hotPosts.value].filter((p) => {
      if (!p || !p.id || seen.has(p.id)) return false
      seen.add(p.id)
      return true
    })
    ensurePostsCovers(allPosts)
  }
}

const syncQuery = () => {
  router.replace({
    query: {
      ...route.query,
      page: String(page.value)
    }
  })
}

const openPost = (post: BlogPost) => {
  if (post.id.startsWith('demo-')) {
    message.info('当前为示例内容，待接口恢复后可点击进入真实文章')
    return
  }
  router.push(`/blog/${post.slug}`)
}

function handleHistoryOpen(item: WatchHistoryItem) {
  openPost(item.post)
}

function handleTagSelect(tag: string) {
  if (tag === '__more__') {
    router.push({ path: '/explore' })
    return
  }
  router.push({ path: '/explore', query: { tags: tag } })
}

function handleCreate() {
  if (!userStore.isLoggedIn) {
    router.push({ path: '/login', query: { redirect: '/create' } })
    return
  }
  router.push('/create')
}

// 监听登录态变化，重新生成浏览历史
watch(
  () => userStore.isLoggedIn,
  () => buildHistoryItems(posts.value)
)

watch(page, async () => {
  syncQuery()
  await fetchPosts()
})

onMounted(async () => {
  await fetchPosts()
})
</script>

<template>
  <div class="home-page">
    <!-- ── Zone 1: 轮播图 ── -->
    <HeroCarousel v-if="hotPosts.length > 0" :posts="hotPosts" :interval="HOT_ROTATE_INTERVAL_MS" />

    <!-- ── Zone 2: 过渡区 · 热门标签云 ── -->
    <TrendingTags
      v-if="trendingTags.length > 0"
      :tags="trendingTags"
      @select="handleTagSelect"
      @create="handleCreate"
    />

    <!-- ── Zone 3: 观看历史（仅登录态） ── -->
    <WatchHistoryStack
      v-if="historyItems.length > 0 && userStore.isLoggedIn"
      :items="historyItems"
      @open="handleHistoryOpen"
    />

    <!-- ── Zone 4: 内容卡片网格 ── -->
    <section v-if="posts.length > 0" class="post-section">
      <div class="section-head">
        <h3>推荐内容</h3>
      </div>
      <div v-if="posts.length === 0" class="empty">暂无内容</div>
      <div v-else class="post-grid">
        <div
          v-for="(post, index) in posts"
          :key="post.id"
          class="grid-item"
          :style="{ animationDelay: `${index * 60}ms` }"
        >
          <PostCard :post="post" mode="compact" @open="openPost(post)" />
        </div>
      </div>
    </section>

    <div v-if="total > 12" class="pager">
      <NPagination
        :page="page"
        :item-count="total"
        :page-size="12"
        @update:page="(val: number) => (page = val)"
      />
    </div>
  </div>
</template>

<style scoped>
.home-page {
  width: 100%;
  max-width: 1440px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: var(--section-gap);
  padding: 0 var(--content-padding) var(--spacing-lg);
  font-family: var(--font-sans);
}

.post-section {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.section-head h3 {
  margin: 0;
  font-size: 18px;
  font-weight: var(--font-weight-semibold);
  color: var(--text-primary);
}

/* ── CSS Grid 弹性网格 ── */
.post-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: var(--spacing-md);
}

.grid-item {
  animation: grid-in 0.5s var(--ease-out-smooth) both;
}

@keyframes grid-in {
  from {
    opacity: 0;
    transform: translateY(12px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.pager {
  display: flex;
  justify-content: center;
  padding-top: var(--spacing-sm);
}

.empty {
  color: var(--text-tertiary);
  padding: var(--spacing-md) 0;
}

/* ── 响应式 ── */
@media (max-width: 700px) {
  .post-grid {
    grid-template-columns: repeat(auto-fill, minmax(170px, 1fr));
  }
}

@media (max-width: 520px) {
  .post-grid {
    grid-template-columns: 1fr;
  }
}
</style>
