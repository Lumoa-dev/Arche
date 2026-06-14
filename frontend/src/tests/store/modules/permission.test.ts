import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { usePermissionStore } from '@/lib/store/modules/permission'

describe('usePermissionStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  describe('初始状态', () => {
    it('默认 level 为 5', () => {
      const store = usePermissionStore()
      expect(store.level).toBe(5)
    })

    it('默认 permissions 为空数组', () => {
      const store = usePermissionStore()
      expect(store.permissions).toEqual([])
    })

    it('routesLoaded 为 false', () => {
      const store = usePermissionStore()
      expect(store.routesLoaded).toBe(false)
    })
  })

  describe('isAdmin', () => {
    it('level 0 为管理员', () => {
      const store = usePermissionStore()
      store.setUserPermission([], 0)
      expect(store.isAdmin()).toBe(true)
    })

    it('level 5 不是管理员', () => {
      const store = usePermissionStore()
      expect(store.isAdmin()).toBe(false)
    })
  })

  describe('hasLevel', () => {
    it('等级数字小等于要求值时有权限', () => {
      const store = usePermissionStore()
      store.setUserPermission([], 2)
      expect(store.hasLevel(2)).toBe(true)
      expect(store.hasLevel(3)).toBe(true)
      expect(store.hasLevel(1)).toBe(false)
    })
  })

  describe('hasPermission', () => {
    it('管理员（level 0）拥有所有权限', () => {
      const store = usePermissionStore()
      store.setUserPermission([], 0)
      expect(store.hasPermission('anything')).toBe(true)
    })

    it('包含 * 通配符拥有所有权限', () => {
      const store = usePermissionStore()
      store.setUserPermission(['*'], 5)
      expect(store.hasPermission('blog:create')).toBe(true)
    })

    it('具体权限匹配', () => {
      const store = usePermissionStore()
      store.setUserPermission(['blog:create', 'blog:edit'], 5)
      expect(store.hasPermission('blog:create')).toBe(true)
      expect(store.hasPermission('blog:delete')).toBe(false)
    })

    it('无权限返回 false', () => {
      const store = usePermissionStore()
      expect(store.hasPermission('anything')).toBe(false)
    })
  })

  describe('setUserPermission', () => {
    it('同时设置 permissions 和 level', () => {
      const store = usePermissionStore()
      store.setUserPermission(['a', 'b'], 1)
      expect(store.permissions).toEqual(['a', 'b'])
      expect(store.level).toBe(1)
    })
  })

  describe('resetPermission', () => {
    it('重置为默认状态', () => {
      const store = usePermissionStore()
      store.setUserPermission(['admin'], 0)
      store.resetPermission()
      expect(store.permissions).toEqual([])
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
