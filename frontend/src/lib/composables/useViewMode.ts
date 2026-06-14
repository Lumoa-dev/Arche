import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

export type ListViewMode = 'compact' | 'detail' | 'card'

export const useViewMode = (storageKey: string, defaultMode: ListViewMode = 'detail') => {
  const route = useRoute()
  const router = useRouter()

  const viewMode = computed<ListViewMode>({
    get() {
      const queryMode = String(route.query.view || '')
      if (queryMode === 'compact' || queryMode === 'detail' || queryMode === 'card') {
        return queryMode
      }
      const saved = localStorage.getItem(storageKey) as ListViewMode | null
      if (saved === 'compact' || saved === 'detail' || saved === 'card') {
        return saved
      }
      return defaultMode
    },
    set(next) {
      localStorage.setItem(storageKey, next)
      router.replace({
        query: {
          ...route.query,
          view: next
        }
      })
    }
  })

  return { viewMode }
}
