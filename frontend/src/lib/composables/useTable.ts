import { ref } from 'vue'

export interface UseTableParams {
  page: number
  pageSize: number
}

export interface UseTableResult<T> {
  list: T[]
  total: number
}

// eslint-disable-next-line no-unused-vars
type UseTableRequest<T> = (_params: UseTableParams) => Promise<UseTableResult<T>>

export const useTable = <T>(request: UseTableRequest<T>) => {
  const loading = ref(false)
  const data = ref<T[]>([])
  const page = ref(1)
  const pageSize = ref(10)
  const total = ref(0)

  const run = async () => {
    loading.value = true
    try {
      const result = await request({
        page: page.value,
        pageSize: pageSize.value
      })
      data.value = result.list
      total.value = result.total
    } finally {
      loading.value = false
    }
  }

  return {
    loading,
    data,
    page,
    pageSize,
    total,
    run
  }
}
