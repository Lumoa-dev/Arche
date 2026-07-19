/**
 * 权限总线 (Permission Bus) 测试
 *
 * 测试核心逻辑：权限缓存管理、页面可访问性判断、组件可见性订阅。
 * 由于 permission-bus 依赖 Vue 的 reactive/computed，测试需要在 Vue 环境下运行。
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

// 模拟 request 模块
vi.mock('@/lib/services/request', () => ({
  get: vi.fn()
}))

describe('permission-bus', () => {
  let permissionBus: typeof import('@/lib/services/permission-bus')
  let get: ReturnType<typeof vi.fn>

  const mockPermissionMap = {
    home: {
      post_card: true,
      trending_tags: false,
      hero_carousel: true
    },
    admin_users: {
      user_table: true,
      user_form: true
    },
    settings: {
      profile_form: false,
      security_form: false
    }
  }

  beforeEach(async () => {
    // 清除 mock 调用记录，避免跨测试污染
    vi.clearAllMocks()
    permissionBus = await import('@/lib/services/permission-bus')
    const mod = await import('@/lib/services/request')
    get = vi.mocked(mod.get)
    get.mockClear()
  })

  afterEach(() => {
    permissionBus.clearPermissionCache()
    vi.clearAllMocks()
  })

  describe('initPermissionBus', () => {
    it('初始化时拉取并缓存权限数据', async () => {
      get.mockResolvedValue(mockPermissionMap)
      await permissionBus.initPermissionBus(0)
      expect(get).toHaveBeenCalledWith('/auth/permissions/pages', { level: 0 })
    })

    it('多次初始化不同 level 应分别缓存', async () => {
      get.mockResolvedValue(mockPermissionMap)
      await permissionBus.initPermissionBus(0)
      await permissionBus.initPermissionBus(1)
      expect(get).toHaveBeenCalledTimes(2)
    })
  })

  describe('canAccessPage', () => {
    it('页面有任一可见组件时应返回 true', async () => {
      get.mockResolvedValue(mockPermissionMap)
      await permissionBus.initPermissionBus(0)
      expect(permissionBus.canAccessPage('home', 0)).toBe(true)
    })

    it('页面所有组件都不可见时应返回 false', async () => {
      get.mockResolvedValue(mockPermissionMap)
      await permissionBus.initPermissionBus(0)
      expect(permissionBus.canAccessPage('settings', 0)).toBe(false)
    })

    it('未缓存的页面应返回 false', async () => {
      get.mockResolvedValue(mockPermissionMap)
      await permissionBus.initPermissionBus(0)
      expect(permissionBus.canAccessPage('nonexistent', 0)).toBe(false)
    })

    it('未缓存的 level 应返回 false', () => {
      expect(permissionBus.canAccessPage('home', 99)).toBe(false)
    })
  })

  describe('getVisiblePages', () => {
    it('应返回有可见组件的页面列表', async () => {
      get.mockResolvedValue(mockPermissionMap)
      await permissionBus.initPermissionBus(0)
      const pages = permissionBus.getVisiblePages(0)
      expect(pages).toContain('home')
      expect(pages).toContain('admin_users')
      expect(pages).not.toContain('settings')
    })

    it('未缓存的 level 应返回空数组', () => {
      expect(permissionBus.getVisiblePages(99)).toEqual([])
    })
  })

  describe('clearPermissionCache', () => {
    it('清空所有缓存', async () => {
      get.mockResolvedValue(mockPermissionMap)
      await permissionBus.initPermissionBus(0)
      permissionBus.clearPermissionCache()
      expect(permissionBus.canAccessPage('home', 0)).toBe(false)
      expect(permissionBus.getVisiblePages(0)).toEqual([])
    })
  })

  describe('refreshPermissionLevel', () => {
    it('强制刷新指定 level 的缓存', async () => {
      get.mockResolvedValue(mockPermissionMap)
      await permissionBus.initPermissionBus(0)
      get.mockResolvedValue({
        ...mockPermissionMap,
        home: { post_card: false, trending_tags: false, hero_carousel: false }
      })
      await permissionBus.refreshPermissionLevel(0)
      expect(permissionBus.canAccessPage('home', 0)).toBe(false)
    })
  })

  describe('getPagePermissions', () => {
    it('获取指定页面的权限映射', async () => {
      get.mockResolvedValue(mockPermissionMap)
      await permissionBus.initPermissionBus(0)
      const perms = await permissionBus.getPagePermissions('home', 0)
      expect(perms).toEqual(mockPermissionMap.home)
    })

    it('不存在的页面返回 null', async () => {
      get.mockResolvedValue(mockPermissionMap)
      await permissionBus.initPermissionBus(0)
      const perms = await permissionBus.getPagePermissions('nonexistent', 0)
      expect(perms).toBeNull()
    })
  })
})