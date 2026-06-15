/**
 * usePostManager — 帖子列表管理和数据获取
 *
 * 负责浏览模式下的帖子列表获取、筛选和统计计算。
 */
import { computed, ref } from 'vue'
import { getMyPostsApi, type BlogPost } from '@/components/logic/api'
import { ensurePostsCovers } from '@/components/logic/useCoverLazyGenerator'

export type PostTab = 'all' | 'published' | 'draft'

export interface StatCard {
  label: string
  value: number
  color: string
}

export function usePostManager() {
  const posts = ref<BlogPost[]>([])
  const loading = ref(false)
  const activeTab = ref<PostTab>('all')

  const totalPosts = computed(() => posts.value.length)
  const draftCount = computed(
    () => posts.value.filter((p) => (p.status || 'draft') === 'draft').length
  )
  const publishedCount = computed(() => posts.value.filter((p) => p.status === 'published').length)
  const totalViews = computed(() => posts.value.reduce((sum, p) => sum + (p.views || 0), 0))

  const statCards = computed<StatCard[]>(() => [
    { label: '全部文章', value: totalPosts.value, color: 'var(--primary-color)' },
    { label: '已发布', value: publishedCount.value, color: 'var(--success-color)' },
    { label: '草稿', value: draftCount.value, color: 'var(--accent-yellow)' },
    { label: '总阅读', value: totalViews.value, color: 'var(--accent-color)' }
  ])

  const filteredPosts = computed(() => {
    if (activeTab.value === 'all') return posts.value
    if (activeTab.value === 'published') {
      return posts.value.filter((p) => p.status === 'published')
    }
    return posts.value.filter((p) => (p.status || 'draft') === 'draft')
  })

  async function fetchData() {
    loading.value = true
    try {
      const res = await getMyPostsApi(
        { page: 1, page_size: 50, sort_by: 'created_at' },
        { silent: true, skipAuthLogout: true }
      )
      posts.value = res.list || []
      // 对缺少封面的旧帖子按需生成文字封面并持久化
      ensurePostsCovers(posts.value)
    } catch {
      posts.value = []
    } finally {
      loading.value = false
    }
  }

  function refreshPosts() {
    return fetchData()
  }

  return { posts, loading, activeTab, filteredPosts, statCards, fetchData, refreshPosts }
}
