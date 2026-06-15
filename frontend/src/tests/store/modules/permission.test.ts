import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { usePermissionStore } from '@/lib/store/modules/permission'

// 模拟权限总线（避免真实的 HTTP 调用）
vi.mock('@/lib/services/permission-bus', () => ({
  initPermissionBus: vi.fn(() => Promise.resolve()),
  clearPermissionCache: vi.fn(),
  canAccessPage: vi.fn(() => true),
  getVisiblePages: vi.fn(() => ['home', 'explore'])
}))

describe('usePermissionStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  describe('初始状态', () => {
    it('默认 level 为 5', () => {
      const store = usePermissionStore()
      expect(store.level).toBe(5)
    })

    it('routesLoaded 为 false', () => {
      const store = usePermissionStore()
      expect(store.routesLoaded).toBe(false)
    })
  })

  describe('isAdmin', () => {
    it('level 0 为管理员', async () => {
      const store = usePermissionStore()
      await store.setUserPermission([], 0)
      expect(store.isAdmin()).toBe(true)
    })

    it('level 5 不是管理员', () => {
      const store = usePermissionStore()
      expect(store.isAdmin()).toBe(false)
    })
  })

  describe('hasLevel', () => {
    it('等级数字小等于要求值时有权限', async () => {
      const store = usePermissionStore()
      await store.setUserPermission([], 2)
      expect(store.hasLevel(2)).toBe(true)
      expect(store.hasLevel(3)).toBe(true)
      expect(store.hasLevel(1)).toBe(false)
    })
  })

  describe('canAccessPage', () => {
    it('委托给权限总线判断页面可访问性', () => {
      const store = usePermissionStore()
      // mock 返回 true，所以 should be true
      expect(store.canAccessPage('admin_users')).toBe(true)
    })
  })

  describe('getVisiblePageList', () => {
    it('返回当前 level 可见页面列表', () => {
      const store = usePermissionStore()
      const pages = store.getVisiblePageList()
      expect(pages).toContain('home')
      expect(pages).toContain('explore')
    })
  })

  describe('setUserPermission', () => {
    it('设置 level 并初始化权限总线', async () => {
      const store = usePermissionStore()
      await store.setUserPermission([], 1)
      expect(store.level).toBe(1)
    })
  })

  describe('resetPermission', () => {
    it('重置为默认状态', async () => {
      const store = usePermissionStore()
      await store.setUserPermission([], 0)
      store.resetPermission()
      expect(store.level).toBe(5)
      expect(store.routesLoaded).toBe(false)
    })
  })

  describe('whiteList', () => {
    it('包含 /login /404 /403', () => {
      const store = usePermissionStore()
      expect(store.whiteList).toContain('/login')
      expect(store.whiteList).toContain('/404')
      expect(store.whiteList).toContain('/403')
    })
  })
})
