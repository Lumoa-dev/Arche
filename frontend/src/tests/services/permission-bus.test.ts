/**
 * 权限总线 (Permission Bus) 行为测试
 *
 * 测试原则：
 * - 只测公开 API 行为，不测内部实现
 * - Mock 掉后端 HTTP 请求，只测权限总线逻辑
 * - 每个测试独立，不依赖执行顺序
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { nextTick } from 'vue'

// Mock 后端请求
const mockGet = vi.fn()
vi.mock('@/lib/services/request', () => ({
  get: mockGet
}))

// 动态导入，让 mock 先生效
let permissionBus: typeof import('@/lib/services/permission-bus')

beforeEach(async () => {
  vi.clearAllMocks()
  // 重新导入以重置 reactive 状态
  permissionBus = await import('@/lib/services/permission-bus')
  permissionBus.clearPermissionCache()
})

describe('initPermissionBus', () => {
  it('拉取后端数据并缓存到指定 level', async () => {
    mockGet.mockResolvedValue({
      home: { post_card: true, hero: false },
      admin: { users_table: true }
    })

    await permissionBus.initPermissionBus(0)

    expect(mockGet).toHaveBeenCalledWith('/auth/permissions/pages', { level: 0 })
  })

  it('多次初始化不同 level 应分别缓存', async () => {
    mockGet
      .mockResolvedValueOnce({ home: { card: true } })
      .mockResolvedValueOnce({ admin: { panel: true } })

    await permissionBus.initPermissionBus(0)
    await permissionBus.initPermissionBus(5)

    expect(mockGet).toHaveBeenCalledTimes(2)
  })
})

describe('getPagePermissions', () => {
  it('缓存命中时直接返回，不发起请求', async () => {
    mockGet.mockResolvedValueOnce({
      home: { post_card: true }
    })

    await permissionBus.initPermissionBus(0)
    mockGet.mockClear()

    const result = await permissionBus.getPagePermissions('home', 0)
    expect(result).toEqual({ post_card: true })
    expect(mockGet).not.toHaveBeenCalled()
  })

  it('缓存未命中时拉取后端', async () => {
    mockGet.mockResolvedValue({
      home: { post_card: true }
    })

    const result = await permissionBus.getPagePermissions('home', 0)
    expect(result).toEqual({ post_card: true })
    expect(mockGet).toHaveBeenCalledWith('/auth/permissions/pages', { level: 0 })
  })

  it('不存在的页面返回 null', async () => {
    mockGet.mockResolvedValue({
      home: { post_card: true }
    })

    await permissionBus.initPermissionBus(0)
    const result = await permissionBus.getPagePermissions('nonexistent', 0)
    expect(result).toBeNull()
  })
})

describe('refreshPermissionLevel', () => {
  it('强制拉取并覆盖缓存', async () => {
    mockGet
      .mockResolvedValueOnce({ home: { card: true } })
      .mockResolvedValueOnce({ home: { card: false } })

    await permissionBus.initPermissionBus(0)
    await permissionBus.refreshPermissionLevel(0)

    const result = await permissionBus.getPagePermissions('home', 0)
    expect(result).toEqual({ card: false })
    expect(mockGet).toHaveBeenCalledTimes(2)
  })
})

describe('usePermission', () => {
  it('页面和组件存在时应返回对应的可见性', () => {
    const { initPermissionBus, usePermission } = permissionBus

    // 先填充缓存
    mockGet.mockResolvedValue({
      home: { post_card: true, hero: false }
    })

    // 使用 await 初始化
    initPermissionBus(0).then(() => {
      const cardVisible = usePermission('home', 'post_card', 0)
      const heroVisible = usePermission('home', 'hero', 0)

      expect(cardVisible.value).toBe(true)
      expect(heroVisible.value).toBe(false)
    })
  })

  it('不存在的页面或组件应返回 false', () => {
    const { initPermissionBus, usePermission } = permissionBus

    mockGet.mockResolvedValue({
      home: { post_card: true }
    })

    initPermissionBus(0).then(() => {
      const result = usePermission('unknown', 'nonexistent', 0)
      expect(result.value).toBe(false)
    })
  })

  it('缓存未初始化时应返回 false', () => {
    const { usePermission } = permissionBus
    const result = usePermission('home', 'post_card', 0)
    expect(result.value).toBe(false)
  })
})

describe('canAccessPage', () => {
  it('页面下任一组件 visible 应返回 true', () => {
    const { initPermissionBus, canAccessPage } = permissionBus

    mockGet.mockResolvedValue({
      admin: { users_table: false, dashboard: true }
    })

    initPermissionBus(0).then(() => {
      expect(canAccessPage('admin', 0)).toBe(true)
    })
  })

  it('页面下所有组件隐藏应返回 false', () => {
    const { initPermissionBus, canAccessPage } = permissionBus

    mockGet.mockResolvedValue({
      admin: { users_table: false, dashboard: false }
    })

    initPermissionBus(0).then(() => {
      expect(canAccessPage('admin', 0)).toBe(false)
    })
  })

  it('不存在的页面应返回 false', () => {
    const { initPermissionBus, canAccessPage } = permissionBus

    mockGet.mockResolvedValue({
      home: { card: true }
    })

    initPermissionBus(0).then(() => {
      expect(canAccessPage('nonexistent', 0)).toBe(false)
    })
  })

  it('缓存未初始化时应返回 false', () => {
    const { canAccessPage } = permissionBus
    expect(canAccessPage('home', 0)).toBe(false)
  })
})

describe('getVisiblePages', () => {
  it('只返回有任一组件可见的页面', () => {
    const { initPermissionBus, getVisiblePages } = permissionBus

    mockGet.mockResolvedValue({
      home: { card: true },
      admin: { panel: false },
      blog: { post: true }
    })

    initPermissionBus(0).then(() => {
      const visible = getVisiblePages(0)
      expect(visible).toContain('home')
      expect(visible).toContain('blog')
      expect(visible).not.toContain('admin')
    })
  })

  it('所有页面隐藏时应返回空数组', () => {
    const { initPermissionBus, getVisiblePages } = permissionBus

    mockGet.mockResolvedValue({
      home: { card: false },
      admin: { panel: false }
    })

    initPermissionBus(0).then(() => {
      expect(getVisiblePages(0)).toEqual([])
    })
  })

  it('缓存未初始化时应返回空数组', () => {
    const { getVisiblePages } = permissionBus
    expect(getVisiblePages(0)).toEqual([])
  })
})

describe('clearPermissionCache', () => {
  it('清空后 canAccessPage 应返回 false', async () => {
    mockGet.mockResolvedValue({
      home: { card: true }
    })

    await permissionBus.initPermissionBus(0)
    permissionBus.clearPermissionCache()

    expect(permissionBus.canAccessPage('home', 0)).toBe(false)
  })

  it('清空后 getVisiblePages 应返回空数组', async () => {
    mockGet.mockResolvedValue({
      home: { card: true }
    })

    await permissionBus.initPermissionBus(0)
    permissionBus.clearPermissionCache()

    expect(permissionBus.getVisiblePages(0)).toEqual([])
  })
})