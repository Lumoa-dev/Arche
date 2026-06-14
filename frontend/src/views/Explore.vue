<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NIcon, NTag } from 'naive-ui'
import { PersonOutline, PricetagOutline } from '@vicons/ionicons5'
import { PostCard } from '@/components/blog'
import { getBlogPostsApi, type BlogPost } from '@/components/logic/api/blog'
import { withFallback } from '@/lib/services/mock'
import { useSearchStore } from '@/lib/store/modules/search'

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

type ExploreFilterMode = 'tag' | 'author'

const filterMode = ref<ExploreFilterMode>('tag')
const selectedTags = ref<string[]>([])
const selectedAuthors = ref<string[]>([])

const router = useRouter()
const route = useRoute()
const searchStore = useSearchStore()

const exploreItems = ref<ExploreItem[]>([])
const allTags = ref<string[]>([])
const allAuthors = ref<string[]>([])
const loading = ref(false)

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
    if (q) {
      params.q = q
    }
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

onMounted(async () => {
  // 从 URL 读取初始筛选参数
  const q = route.query
  if (q.mode === 'tag' || q.mode === 'author') filterMode.value = q.mode
  if (q.tags) selectedTags.value = String(q.tags).split(',').filter(Boolean)
  if (q.authors) selectedAuthors.value = String(q.authors).split(',').filter(Boolean)

  await fetchExploreData()
})

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

// 监听全局搜索关键词变化
let searchTimer: ReturnType<typeof setTimeout> | null = null
watch(
  () => searchStore.keyword,
  () => {
    if (searchTimer) clearTimeout(searchTimer)
    searchTimer = setTimeout(() => {
      fetchExploreData()
    }, 400)
  }
)

const isOptionChecked = (option: string) => {
  if (filterMode.value === 'tag') {
    return option === '全部' ? selectedTags.value.length === 0 : selectedTags.value.includes(option)
  }
  return option === '全部作者'
    ? selectedAuthors.value.length === 0
    : selectedAuthors.value.includes(option)
}

const toggleSidebarOption = (option: string) => {
  if (filterMode.value === 'tag') {
    if (option === '全部') {
      selectedTags.value = []
      return
    }
    selectedTags.value = selectedTags.value.includes(option)
      ? selectedTags.value.filter((tag) => tag !== option)
      : [...selectedTags.value, option]
    return
  }
  if (option === '全部作者') {
    selectedAuthors.value = []
    return
  }
  selectedAuthors.value = selectedAuthors.value.includes(option)
    ? selectedAuthors.value.filter((author) => author !== option)
    : [...selectedAuthors.value, option]
}

type CompoundFilterChip = {
  type: '标签' | '用户'
  value: string
}

const activeCompoundFilters = computed<CompoundFilterChip[]>(() => [
  ...(selectedTags.value.length > 0
    ? selectedTags.value.map((value) => ({ type: '标签' as const, value }))
    : []),
  ...(selectedAuthors.value.length > 0
    ? selectedAuthors.value.map((value) => ({ type: '用户' as const, value }))
    : [])
])

function toBlogPost(item: ExploreItem): BlogPost {
  return {
    id: String(item.id),
    slug: item.title,
    title: item.title,
    introduction: { abstract: item.content || item.excerpt },
    tags: item.tags,
    author_username: item.author,
    created_at: item.date,
    likes: item.likes,
    views: 0
  }
}

const handleOpenItem = (post: BlogPost) => {
  router.push(`/blog/${post.slug}`)
}

const handleCompoundFilterChipClick = (chip: CompoundFilterChip) => {
  if (chip.type === '标签') {
    selectedTags.value = selectedTags.value.filter((tag) => tag !== chip.value)
    return
  }
  selectedAuthors.value = selectedAuthors.value.filter((author) => author !== chip.value)
}

const visibleTags = computed(() => allTags.value)

const visibleAuthors = computed(() => allAuthors.value)

const tagThemeOverrides = {
  borderRadius: '8px',
  colorChecked: 'var(--primary-color)',
  colorCheckedHover: 'var(--primary-hover-color)',
  colorCheckedPressed: 'var(--primary-pressed-color)',
  textColorChecked: '#fff',
  border: 'none',
  padding: '0 14px',
  height: '30px',
  fontSize: '13px',
  color: 'var(--surface-color)',
  textColor: 'var(--text-primary)',
  colorCheckable: 'transparent',
  colorHoverCheckable: 'var(--surface-hover-color)'
}

const filteredItems = computed(() => {
  let list = [...exploreItems.value]

  if (selectedAuthors.value.length > 0) {
    list = list.filter((item) => selectedAuthors.value.includes(item.author))
  }

  if (selectedTags.value.length > 0) {
    list = list.filter((item) => item.tags.some((tag: string) => selectedTags.value.includes(tag)))
  }

  list.sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime())
  return list
})
</script>

<template>
  <div class="explore-page">
    <section class="explore-body">
      <aside class="tag-sidebar">
        <div class="filter-tabs">
          <button
            class="filter-tab"
            :class="{ active: filterMode === 'tag' }"
            type="button"
            @click="filterMode = 'tag'"
          >
            <NIcon size="14" aria-hidden="true">
              <PricetagOutline />
            </NIcon>
            <span>标签</span>
          </button>
          <button
            class="filter-tab"
            :class="{ active: filterMode === 'author' }"
            type="button"
            @click="filterMode = 'author'"
          >
            <NIcon size="14" aria-hidden="true">
              <PersonOutline />
            </NIcon>
            <span>用户</span>
          </button>
        </div>
        <Transition name="tag-stack-panel" mode="out-in">
          <div :key="filterMode" class="tag-stack">
            <NTag
              v-for="option in filterMode === 'tag' ? visibleTags : visibleAuthors"
              :key="option"
              checkable
              :checked="isOptionChecked(option)"
              class="stack-tag"
              :theme-overrides="tagThemeOverrides"
              @update:checked="() => toggleSidebarOption(option)"
            >
              {{ option }}
            </NTag>
          </div>
        </Transition>
      </aside>

      <main class="content">
        <section class="content-display-panel">
          <div v-if="activeCompoundFilters.length > 0" class="filter-bar">
            <TransitionGroup name="filter-chip" tag="div" class="filter-chip-list">
              <button
                v-for="chip in activeCompoundFilters"
                :key="`${chip.type}-${chip.value}`"
                type="button"
                class="filter-chip"
                @click="handleCompoundFilterChipClick(chip)"
              >
                <span class="chip-label">{{ chip.type }}</span>
                <span class="chip-value">{{ chip.value }}</span>
                <span class="chip-close" aria-hidden="true">×</span>
              </button>
            </TransitionGroup>
          </div>
          <div class="explore-grid">
            <PostCard
              v-for="item in filteredItems"
              :key="item.id"
              :post="toBlogPost(item)"
              mode="dense"
              @open="handleOpenItem"
            />
          </div>
        </section>
      </main>
    </section>
  </div>
</template>

<style scoped>
.explore-page {
  width: min(1200px, 100%);
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: var(--layout-gap);
  font-family: var(--font-sans);
}

.header {
  display: flex;
  justify-content: space-between;
  gap: var(--spacing-lg);
  align-items: center;
}

.header-title p {
  margin: 0;
  color: var(--text-tertiary);
  font-size: 13px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.header-title h1 {
  margin: 6px 0 0;
  font-size: 28px;
}

.explore-body {
  display: grid;
  grid-template-columns: minmax(280px, 300px) minmax(0, 1fr);
  gap: var(--layout-gap);
  overflow: visible;
  align-items: start;
}

.tag-sidebar {
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  align-items: center;
  gap: var(--spacing-md);
  width: 100%;
  max-width: 320px;
  min-height: 360px;
  padding: var(--spacing-md);
  box-sizing: border-box;
  position: sticky;
  top: 87px;
  align-self: start;
  max-height: calc(100vh - 87px);
  overflow-y: auto;
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
}

.filter-tabs {
  display: flex;
  gap: 4px;
  width: 100%;
  background: var(--bg-inset-color);
  border-radius: var(--radius-md);
  padding: 3px;
  border: 1px solid var(--border-color);
  box-sizing: border-box;
}

.filter-tab {
  flex: 1;
  height: 32px;
  border: 0;
  border-radius: calc(var(--radius-md) - 2px);
  background: transparent;
  color: var(--text-tertiary);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  font-size: 13px;
  cursor: pointer;
  transition: all var(--transition-fast);
  font-family: var(--font-sans);
}

.filter-tab.active {
  background: var(--surface-color);
  color: var(--text-primary);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
}

.tag-stack {
  display: flex;
  flex-wrap: wrap;
  flex: 1;
  gap: 8px;
  overflow-y: auto;
  min-height: 0;
  width: 100%;
  margin: 0;
  padding: var(--spacing-md);
  box-sizing: border-box;
  align-content: flex-start;
  background: var(--bg-inset-color);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-color);
}

.stack-tag {
  margin: 0;
  transition: transform var(--transition-fast);
}

.stack-tag:hover {
  transform: translateY(-1px);
}

.tag-stack-panel-enter-active,
.tag-stack-panel-leave-active {
  transition:
    opacity var(--transition-normal),
    transform var(--transition-normal);
}

.tag-stack-panel-enter-from,
.tag-stack-panel-leave-to {
  opacity: 0;
  transform: translateY(4px);
}

.content {
  min-height: 360px;
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.content-display-panel {
  flex: 1;
  min-height: 0;
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-color);
  background: var(--surface-color);
  padding: var(--content-padding);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.filter-bar {
  margin-bottom: 4px;
}

.filter-chip-list {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.filter-chip {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 4px 10px 4px 12px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-full);
  background: var(--surface-color);
  cursor: pointer;
  font-family: var(--font-sans);
  font-size: 12px;
  transition: all var(--transition-fast);
}

.filter-chip:hover {
  background: var(--surface-strong-color);
  border-color: var(--text-tertiary);
}

.chip-label {
  color: var(--text-tertiary);
}

.chip-value {
  color: var(--text-primary);
  font-weight: var(--font-weight-medium);
}

.chip-close {
  color: var(--text-tertiary);
  font-size: 14px;
  line-height: 1;
  margin-left: 2px;
}

.filter-chip:hover .chip-close {
  color: var(--error-color);
}

.filter-chip-enter-active,
.filter-chip-leave-active {
  transition: all var(--transition-normal);
}

.filter-chip-enter-from,
.filter-chip-leave-to {
  opacity: 0;
  transform: translateY(4px) scale(0.96);
}

.filter-chip-move {
  transition: transform var(--transition-normal);
}

.explore-grid {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: var(--spacing-md);
  align-content: start;
}

@media (max-width: 1100px) {
  .header {
    flex-direction: column;
    align-items: stretch;
  }

  .tag-sidebar {
    min-height: 360px;
  }

  .tag-stack {
    max-height: 180px;
  }
}
</style>
