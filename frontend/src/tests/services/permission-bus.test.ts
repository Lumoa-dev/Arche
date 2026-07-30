import { describe, it, expect, vi, beforeEach } from 'vitest'
import { computed, ref } from 'vue'

// 完全 mock request 模块
vi.mock('@/lib/services/request', () => ({
  get: vi.fn()
}))

beforeEach(() => {
  vi.clearAllMocks()
})

describe('permission-bus', () => {
  it('initPermissionBus 拉取并缓存权限数据', async () => {
    const { initPermissionBus, getPagePermissions } = await import('@/lib/services/permission-bus')
    const { get } = await import('@/lib/services/request')

    vi.mocked(get).mockResolvedValue({
      home: { post_card: true, sidebar: false },
      admin: { users: true }
    })

    await initPermissionBus(0)

    // 缓存应生效
    const homePerms = await getPagePermissions('home', 0)
    expect(homePerms).toEqual({ post_card: true, sidebar: false })

    const adminPerms = await getPagePermissions('admin', 0)
    expect(adminPerms).toEqual({ users: true })
  })

  it('refreshPermissionLevel 强制拉取', async () => {
    const { refreshPermissionLevel, getPagePermissions } = await import('@/lib/services/permission-bus')
    const { get } = await import('@/lib/services/request')

    vi.mocked(get)
      .mockResolvedValueOnce({ old: { comp: true } })
      .mockResolvedValueOnce({ new: { comp: false } })

    await refreshPermissionLevel(1)
    const oldPerms = await getPagePermissions('old', 1)
    expect(oldPerms).toEqual({ comp: true })

    // 再次刷新
    await refreshPermissionLevel(1)
    const newPerms = await getPagePermissions('new', 1)
    expect(newPerms).toEqual({ comp: false })
  })

  it('usePermission 返回响应式 ComputedRef', async () => {
    const { initPermissionBus, usePermission } = await import('@/lib/services/permission-bus')
    const { get } = await import('@/lib/services/request')

    vi.mocked(get).mockResolvedValue({
      home: { post_card: true, secret: false }
    })

    await initPermissionBus(0)

    const visible = usePermission('home', 'post_card', 0)
    expect(visible.value).toBe(true)

    const hidden = usePermission('home', 'secret', 0)
    expect(hidden.value).toBe(false)
  })

  it('usePermission 返回 false 当页面不存在', async () => {
    const { usePermission } = await import('@/lib/services/permission-bus')

    const result = usePermission('nonexistent', 'comp', 999)
    expect(result.value).toBe(false)
  })

  it('canAccessPage 判断页面可访问性', async () => {
    const { initPermissionBus, canAccessPage } = await import('@/lib/services/permission-bus')
    const { get } = await import('@/lib/services/request')

    vi.mocked(get).mockResolvedValue({
      home: { post_card: true, sidebar: false },
      admin: { users: false, settings: false }
    })

    await initPermissionBus(0)

    expect(canAccessPage('home', 0)).toBe(true)
    expect(canAccessPage('admin', 0)).toBe(false)
  })

  it('getVisiblePages 返回有可见组件的页面', async () => {
    const { initPermissionBus, getVisiblePages } = await import('@/lib/services/permission-bus')
    const { get } = await import('@/lib/services/request')

    vi.mocked(get).mockResolvedValue({
      home: { post_card: true },
      admin: { users: false },
      blog: { create: true }
    })

    await initPermissionBus(0)

    const pages = getVisiblePages(0)
    expect(pages).toContain('home')
    expect(pages).toContain('blog')
    expect(pages).not.toContain('admin')
  })

  it('clearPermissionCache 清空所有缓存', async () => {
    const { initPermissionBus, clearPermissionCache, canAccessPage } = await import('@/lib/services/permission-bus')
    const { get } = await import('@/lib/services/request')

    vi.mocked(get).mockResolvedValue({
      home: { post_card: true }
    })

    await initPermissionBus(0)
    expect(canAccessPage('home', 0)).toBe(true)

    clearPermissionCache()
    expect(canAccessPage('home', 0)).toBe(false)
  })

  it('getPagePermissions 返回 null 当页面不存在', async () => {
    const { getPagePermissions } = await import('@/lib/services/permission-bus')

    const result = await getPagePermissions('nonexistent', 999)
    expect(result).toBeNull()
  })
})