import { describe, it, expect, vi, beforeEach } from 'vitest'

vi.mock('@/lib/services/request', () => ({
  get: vi.fn(),
  post: vi.fn(),
  put: vi.fn(),
  del: vi.fn()
}))

beforeEach(() => {
  vi.clearAllMocks()
})

describe('config API', () => {
  it('getConfigListApi', async () => {
    const { getConfigListApi } = await import('@/lib/services/api/config')
    const { get } = await import('@/lib/services/request')
    vi.mocked(get).mockResolvedValue([])
    await getConfigListApi({ group: 'oss' })
    expect(get).toHaveBeenCalledWith('/admin/config', { group: 'oss' }, undefined)
  })

  it('getConfigItemApi 拼接 key 路径', async () => {
    const { getConfigItemApi } = await import('@/lib/services/api/config')
    const { get } = await import('@/lib/services/request')
    vi.mocked(get).mockResolvedValue({ key: 'FOO', value: 'bar' })
    await getConfigItemApi('FOO')
    expect(get).toHaveBeenCalledWith('/admin/config/FOO', undefined, undefined)
  })

  it('updateConfigItemApi 拼接 key 路径并传递 value', async () => {
    const { updateConfigItemApi } = await import('@/lib/services/api/config')
    const { put } = await import('@/lib/services/request')
    vi.mocked(put).mockResolvedValue({ key: 'FOO', value: 'new' })
    await updateConfigItemApi('FOO', 'new')
    expect(put).toHaveBeenCalledWith('/admin/config/FOO', { value: 'new' }, undefined)
  })

  it('getConfigGroupsApi', async () => {
    const { getConfigGroupsApi } = await import('@/lib/services/api/config')
    const { get } = await import('@/lib/services/request')
    vi.mocked(get).mockResolvedValue(['oss', 'cloud'])
    await getConfigGroupsApi()
    expect(get).toHaveBeenCalledWith('/admin/config/groups', undefined, undefined)
  })

  it('reloadConfigApi 发送 POST', async () => {
    const { reloadConfigApi } = await import('@/lib/services/api/config')
    const { post } = await import('@/lib/services/request')
    vi.mocked(post).mockResolvedValue(undefined)
    await reloadConfigApi()
    expect(post).toHaveBeenCalledWith('/admin/config/reload', undefined, undefined)
  })
})
