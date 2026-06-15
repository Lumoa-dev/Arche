import { ref, type Ref } from 'vue'
import { withFallback, type WithFallbackOptions } from '@/lib/services/mock'

export interface UseApiWithFallbackResult<T> {
  data: Ref<T>
  loading: Ref<boolean>
  error: Ref<Error | null>
  isFallback: Ref<boolean>
  refresh: () => Promise<void>
}

export const useApiWithFallback = <T>(
  fetcher: () => Promise<T>,
  mockData: T,
  options: WithFallbackOptions = {}
): UseApiWithFallbackResult<T> => {
  const data = ref<T>(mockData) as Ref<T>
  const loading = ref(false)
  const error = ref<Error | null>(null)
  const isFallback = ref(true)

  const refresh = async () => {
    loading.value = true
    error.value = null
    try {
      const result = await withFallback(fetcher, mockData, options)
      data.value = result
      isFallback.value = result === mockData
    } catch (err) {
      error.value = err instanceof Error ? err : new Error(String(err))
      data.value = mockData
      isFallback.value = true
    } finally {
      loading.value = false
    }
  }

  return {
    data,
    loading,
    error,
    isFallback,
    refresh
  }
}
