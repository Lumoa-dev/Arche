import { describe, it, expect, vi } from 'vitest'
import { useTable } from '@/lib/composables/useTable'

describe('useTable', () => {
  it('初始状态：空列表、零总数、第一页、每页 10 条、未加载', () => {
    const request = vi.fn()
    const table = useTable(request)

    expect(table.data.value).toEqual([])
    expect(table.total.value).toBe(0)
    expect(table.page.value).toBe(1)
    expect(table.pageSize.value).toBe(10)
    expect(table.loading.value).toBe(false)
  })

  it('run() 调用 request 并传入正确的分页参数', async () => {
    const request = vi.fn().mockResolvedValue({ list: [], total: 0 })
    const table = useTable(request)

    table.page.value = 3
    table.pageSize.value = 20
    await table.run()

    expect(request).toHaveBeenCalledWith({ page: 3, pageSize: 20 })
  })

  it('run() 更新 data 和 total', async () => {
    const mockData = [
      { id: 1, name: 'A' },
      { id: 2, name: 'B' }
    ]
    const request = vi.fn().mockResolvedValue({ list: mockData, total: 50 })
    const table = useTable(request)

    await table.run()

    expect(table.data.value).toEqual(mockData)
    expect(table.total.value).toBe(50)
  })

  it('run() 过程中 loading 变化正确', async () => {
    const request = vi.fn().mockResolvedValue({ list: [], total: 0 })
    const table = useTable(request)

    const promise = table.run()
    expect(table.loading.value).toBe(true)

    await promise
    expect(table.loading.value).toBe(false)
  })

  it('run() 即使 request 抛出异常，loading 也重置为 false', async () => {
    const request = vi.fn().mockRejectedValue(new Error('network error'))
    const table = useTable(request)

    await expect(table.run()).rejects.toThrow('network error')
    expect(table.loading.value).toBe(false)
  })
})
