<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getBlogPostsApi, type BlogPost } from '@/components/logic/api/blog'
import { withFallback } from '@/lib/services/mock'
import { useSearchStore } from '@/lib/store/modules/search'
import PostCardForDense from '@/components/widgets/blog/PostCardForDense.vue'
import ExploreSidebar from '@/components/widgets/explore/ExploreSidebar.vue'
import ArPage from '@/components/ui/ArPage.vue'
import ArHBox from '@/components/ui/ArHBox.vue'

interface ExploreItem {
  id: number
  title: string
  author: string
  tags: string[]
  date: string
  likes: number
  favorites: number
  content: string
  excerpt: string
  cover: string
}

const router = useRouter()
const route = useRoute()
const searchStore = useSearchStore()

const exploreItems = ref<ExploreItem[]>([])
const allTags = ref<string[]>([])
const allAuthors = ref<string[]>([])
const loading = ref(false)
const filterMode = ref<'tag' | 'author'>('tag')
const selectedTags = ref<string[]>([])
const selectedAuthors = ref<string[]>([])

const convertBlogPostToExploreItem = (post: BlogPost, index: number): ExploreItem => {
  const gradientCovers = [
    'linear-gradient(135deg, #f2dfc7, #dcbca0)',
    'linear-gradient(135deg, #d9c8b0, #9f8169)',
    'linear-gradient(135deg, #e8d7bf, #c0a688)',
    'linear-gradient(135deg, #d0c2b1, #8f7560)'
  ]
  return {
    id: index + 1,
    title: post.title || '',
    author: post.author_username || '匿名',
    tags: post.tags || [],
    date: (post.created_at || '').slice(0, 10),
    likes: post.likes || 0,
    favorites: Math.max(1, Math.round((post.likes || 0) * 0.65)),
    content: post.introduction?.abstract ?? '',
    excerpt: (post.introduction?.abstract ?? '').slice(0, 60),
    cover: gradientCovers[index % gradientCovers.length] ?? ''
  }
}

const fetchExploreData = async () => {
  loading.value = true
  try {
    const params: Record<string, unknown> = { page: 1, page_size: 20, sort_by: 'created_at' }
    const q = searchStore.keyword.trim()
    if (q) params.q = q
    const result = await withFallback(
      () => getBlogPostsApi(params),
      { list: [], total: 0, page: 0, page_size: 0 },
      { silent: true }
    )
    const list = result.list || []
    exploreItems.value = list.map(convertBlogPostToExploreItem)
    const tagSet = new Set<string>()
    const authorSet = new Set<string>()
    list.forEach((post) => {
      ;(post.tags || []).forEach((tag) => tagSet.add(tag))
      if (post.author_username) authorSet.add(post.author_username)
    })
    allTags.value = ['全部', ...Array.from(tagSet)]
    allAuthors.value = ['全部作者', ...Array.from(authorSet)]
  } catch {
    exploreItems.value = []
    allTags.value = ['全部']
    allAuthors.value = ['全部作者']
  } finally {
    loading.value = false
  }
}

const filteredItems = computed(() => {
  let list = [...exploreItems.value]
  if (selectedAuthors.value.length > 0) {
    list = list.filter((item) => selectedAuthors.value.includes(item.author))
  }
  if (selectedTags.value.length > 0) {
    list = list.filter((item) => item.tags.some((tag) => selectedTags.value.includes(tag)))
  }
  list.sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime())
  return list
})

const toBlogPost = (item: ExploreItem): BlogPost => ({
  id: String(item.id),
  slug: item.title,
  title: item.title,
  introduction: { abstract: item.content || item.excerpt },
  tags: item.tags,
  author_username: item.author,
  created_at: item.date,
  likes: item.likes,
  views: 0
})

const handleOpenItem = (post: BlogPost) => {
  router.push(`/blog/${post.slug}`)
}

// 从 URL 读取初始筛选参数
onMounted(async () => {
  const q = route.query
  if (q.mode === 'tag' || q.mode === 'author') filterMode.value = q.mode
  if (q.tags) selectedTags.value = String(q.tags).split(',').filter(Boolean)
  if (q.authors) selectedAuthors.value = String(q.authors).split(',').filter(Boolean)
  await fetchExploreData()
})

// URL 同步
watch(
  [filterMode, selectedTags, selectedAuthors],
  () => {
    const query: Record<string, string> = {}
    if (filterMode.value !== 'tag') query.mode = filterMode.value
    if (selectedTags.value.length > 0) query.tags = selectedTags.value.join(',')
    if (selectedAuthors.value.length > 0) query.authors = selectedAuthors.value.join(',')
    const keys = Object.keys(query)
    router.replace(keys.length ? { path: route.path, query } : { path: route.path })
  },
  { deep: true }
)

// 搜索关键词变化
let searchTimer: ReturnType<typeof setTimeout> | null = null
watch(
  () => searchStore.keyword,
  () => {
    if (searchTimer) clearTimeout(searchTimer)
    searchTimer = setTimeout(() => fetchExploreData(), 400)
  }
)
</script>

<template>
  <ArPage style="width: min(1200px, 100%); margin: 0 auto">
    <ArHBox gap="var(--layout-gap)" align="start">
      <ExploreSidebar
        :filter-mode="filterMode"
        :selected-tags="selectedTags"
        :selected-authors="selectedAuthors"
        :all-tags="allTags"
        :all-authors="allAuthors"
        @update:filterMode="filterMode = $event"
        @update:selectedTags="selectedTags = $event"
        @update:selectedAuthors="selectedAuthors = $event"
      />

      <ArHBox wrap gap="var(--spacing-md)" style="flex: 1; min-width: 0; align-content: start">
        <div v-for="item in filteredItems" :key="item.id" style="flex: 1; min-width: 220px">
          <PostCardForDense :post="toBlogPost(item)" @open="handleOpenItem" />
        </div>
      </ArHBox>
    </ArHBox>
  </ArPage>
</template>
