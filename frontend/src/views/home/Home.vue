<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NPagination, useMessage } from 'naive-ui'
import { getBlogPostsApi, type BlogPost } from '@/components/logic/api/blog'
import { withFallback, blogMockData } from '@/lib/services/mock'
import { useUserStore } from '@/lib/store/modules/user'
import { HeroCarousel, TrendingTags, WatchHistoryStack } from '@/components/widgets'
import PostCardForCompact from '@/components/widgets/blog/PostCardForCompact.vue'
import ArPage from '@/components/ui/ArPage.vue'
import ArVBox from '@/components/ui/ArVBox.vue'
import ArHBox from '@/components/ui/ArHBox.vue'
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
  <ArPage
    maxWidth="1440px"
    padding="0 var(--content-padding) var(--spacing-lg)"
    style="margin: 0 auto"
  >
    <ArVBox gap="var(--section-gap)">
      <!-- Zone 1: 轮播图 -->
      <HeroCarousel
        v-if="hotPosts.length > 0"
        :posts="hotPosts"
        :interval="HOT_ROTATE_INTERVAL_MS"
      />

      <!-- Zone 2: 热门标签云 -->
      <TrendingTags
        v-if="trendingTags.length > 0"
        :tags="trendingTags"
        @select="handleTagSelect"
        @create="handleCreate"
      />

      <!-- Zone 3: 观看历史 -->
      <WatchHistoryStack
        v-if="historyItems.length > 0 && userStore.isLoggedIn"
        :items="historyItems"
        @open="handleHistoryOpen"
      />

      <!-- Zone 4: 推荐内容 -->
      <ArVBox v-if="posts.length > 0" gap="var(--spacing-md)">
        <h3
          style="
            margin: 0;
            font-size: 18px;
            font-weight: var(--font-weight-semibold);
            color: var(--text-primary);
          "
        >
          推荐内容
        </h3>
        <ArHBox wrap gap="var(--spacing-md)">
          <div v-for="(post, index) in posts" :key="post.id" style="flex: 1; min-width: 200px">
            <PostCardForCompact :post="post" :delay="index * 60" @open="openPost(post)" />
          </div>
        </ArHBox>
      </ArVBox>

      <!-- 空状态 -->
      <div
        v-if="posts.length === 0"
        style="color: var(--text-tertiary); padding: var(--spacing-md) 0"
      >
        暂无内容
      </div>

      <!-- 分页 -->
      <ArHBox v-if="total > 12" justify="center" style="padding-top: var(--spacing-sm)">
        <NPagination
          :page="page"
          :item-count="total"
          :page-size="12"
          @update:page="(val: number) => (page = val)"
        />
      </ArHBox>
    </ArVBox>
  </ArPage>
</template>
