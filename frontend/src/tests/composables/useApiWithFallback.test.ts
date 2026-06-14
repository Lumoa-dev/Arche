import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useApiWithFallback } from '@/lib/composables/useApiWithFallback'

// withFallback 的内部逻辑依赖 $message，这里 mock 掉
vi.mock('@/utils/message', () => ({
  $message: { warning: vi.fn(), success: vi.fn() }
}))

describe('useApiWithFallback', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('初始状态：data 为 mockData，loading 为 false，error 为 null，isFallback 为 true', () => {
    const result = useApiWithFallback(() => Promise.resolve('real'), 'mock')

    expect(result.data.value).toBe('mock')
    expect(result.loading.value).toBe(false)
    expect(result.error.value).toBeNull()
    expect(result.isFallback.value).toBe(true)
  })

  it('refresh() 成功后 data 使用真实值，isFallback 为 false', async () => {
    const fetcher = vi.fn().mockResolvedValue('real-data')
    const result = useApiWithFallback(fetcher, 'mock')

    await result.refresh()

    expect(result.data.value).toBe('real-data')
    expect(result.loading.value).toBe(false)
    expect(result.isFallback.value).toBe(false)
    expect(result.error.value).toBeNull()
  })

  it('refresh() 网络错误时 fallback 到 mockData，isFallback 为 true', async () => {
    // 模拟网络错误：withFallback 内部捕获网络错误并返回 mockData
    const fetcher = vi
      .fn()
      .mockRejectedValue({ isAxiosError: true, response: undefined, code: 'ERR_NETWORK' })
    const result = useApiWithFallback(fetcher, 'fallback-data')

    await result.refresh()

    expect(result.data.value).toBe('fallback-data')
    expect(result.isFallback.value).toBe(true)
    expect(result.loading.value).toBe(false)
  })

  it('refresh() 非网络错误时捕获异常，设置 error 并回退到 mockData', async () => {
    const appError = new Error('业务错误')
    const fetcher = vi.fn().mockRejectedValue(appError)
    const result = useApiWithFallback(fetcher, 'mock')

    // refresh 内部有 catch，不会向外抛
    await result.refresh()

    expect(result.error.value).toBeDefined()
    expect(result.error.value!.message).toBe('业务错误')
    // data 回退到 mockData
    expect(result.data.value).toBe('mock')
    expect(result.isFallback.value).toBe(true)
    expect(result.loading.value).toBe(false)
  })

  it('refresh() 过程中 loading 为 true', async () => {
    let resolveFn!: (v: string) => void // eslint-disable-line no-unused-vars
    const fetcher = vi.fn().mockReturnValue(
      new Promise<string>((resolve) => {
        resolveFn = resolve
      })
    )
    const result = useApiWithFallback(fetcher, 'mock')

    const promise = result.refresh()
    expect(result.loading.value).toBe(true)

    resolveFn('done')
    await promise
    expect(result.loading.value).toBe(false)
  })
})
