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

describe('users API', () => {
  it('getUsersApi', async () => {
    const { getUsersApi } = await import('@/lib/services/api/users')
    const { get } = await import('@/lib/services/request')
    vi.mocked(get).mockResolvedValue({ items: [], total: 0 })
    await getUsersApi({ page: 1, page_size: 20 })
    expect(get).toHaveBeenCalledWith('/auth/users', { page: 1, page_size: 20 }, undefined)
  })

  it('getUserDetailApi 拼接 userId', async () => {
    const { getUserDetailApi } = await import('@/lib/services/api/users')
    const { get } = await import('@/lib/services/request')
    vi.mocked(get).mockResolvedValue({ id: 'u1' })
    await getUserDetailApi('u1')
    expect(get).toHaveBeenCalledWith('/auth/users/u1', undefined, undefined)
  })

  it('updateUserApi 拼接 userId', async () => {
    const { updateUserApi } = await import('@/lib/services/api/users')
    const { put } = await import('@/lib/services/request')
    vi.mocked(put).mockResolvedValue({ id: 'u1' })
    await updateUserApi('u1', { level: 0 })
    expect(put).toHaveBeenCalledWith('/auth/users/u1', { level: 0 }, undefined)
  })

  it('disableUserApi POST 到正确路径', async () => {
    const { disableUserApi } = await import('@/lib/services/api/users')
    const { post } = await import('@/lib/services/request')
    vi.mocked(post).mockResolvedValue(undefined)
    await disableUserApi('u1')
    expect(post).toHaveBeenCalledWith('/auth/users/u1/disable', undefined, undefined)
  })

  it('createAdminUserApi POST 到 admin 路径', async () => {
    const { createAdminUserApi } = await import('@/lib/services/api/users')
    const { post } = await import('@/lib/services/request')
    vi.mocked(post).mockResolvedValue({ id: 'new' })
    await createAdminUserApi({ email: 'a@b.com', username: 'newuser', password: 'pass' })
    expect(post).toHaveBeenCalledWith(
      '/auth/admin/users',
      { email: 'a@b.com', username: 'newuser', password: 'pass' },
      undefined
    )
  })
})
