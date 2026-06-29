/**
 * 权限总线 (Permission Bus) 单元测试
 *
 * 测试覆盖：
 * - 缓存初始化和缓存命中/穿透
 * - 页面级访问控制
 * - 组件级可见性订阅
 * - 侧边栏可见页面生成
 * - 缓存过期和刷新机制
 * - 缓存清理
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import {
  initPermissionBus,
  refreshPermissionLevel,
  getPagePermissions,
  canAccessPage,
  getVisiblePages,
  clearPermissionCache,
  usePermission
} from '@/lib/services/permission-bus'

// ── Mock 后端请求 ──

const mockGet = vi.fn()
vi.mock('@/lib/services/request', () => ({
  get: (...args: any[]) => mockGet(...args)
}))

// ── 测试数据 ──

const mockPermissions = {
  home: {
    post_card: true,
    sidebar: false,
    hero: true
  },
  admin_users: {
    user_table: true,
    filter_bar: true
  },
  admin_settings: {
    config_form: false,
    save_button: false
  }
}

describe('initPermissionBus', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    clearPermissionCache()
  })

  it('应拉取并缓存指定 level 的权限数据', async () => {
    mockGet.mockResolvedValue(mockPermissions)

    await initPermissionBus(5)

    expect(mockGet).toHaveBeenCalledWith('/auth/permissions/pages', { level: 5 })
  })

  it('后续 getPagePermissions 应从缓存读取', async () => {
    mockGet.mockResolvedValue(mockPermissions)

    await initPermissionBus(5)
    mockGet.mockClear()

    const result = await getPagePermissions('home', 5)
    expect(result).toEqual(mockPermissions.home)
    expect(mockGet).not.toHaveBeenCalled() // 不触发拉取
  })
})

describe('refreshPermissionLevel', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    clearPermissionCache()
  })

  it('应强制拉取新数据并覆盖缓存', async () => {
    mockGet.mockResolvedValueOnce(mockPermissions)
    await initPermissionBus(5)

    const newPermissions = {
      home: { post_card: false }
    }
    mockGet.mockResolvedValueOnce(newPermissions)
    await refreshPermissionLevel(5)

    const result = await getPagePermissions('home', 5)
    expect(result).toEqual(newPermissions.home)
  })
})

describe('getPagePermissions', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    clearPermissionCache()
  })

  it('缓存未命中时应拉取新数据', async () => {
    mockGet.mockResolvedValue(mockPermissions)

    const result = await getPagePermissions('home', 3)
    expect(mockGet).toHaveBeenCalled()
    expect(result).toEqual(mockPermissions.home)
  })

  it('不存在的页面应返回 null', async () => {
    mockGet.mockResolvedValue(mockPermissions)
    await initPermissionBus(5)

    // 缓存已就绪
    const result = await getPagePermissions('nonexistent_page', 5)
    expect(result).toBeNull()
  })
})

describe('canAccessPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    clearPermissionCache()
  })

  it('任一组件可见时页面可访问', async () => {
    mockGet.mockResolvedValue(mockPermissions)
    await initPermissionBus(0)

    expect(canAccessPage('home', 0)).toBe(true)
  })

  it('所有组件不可见时页面不可访问', async () => {
    const hiddenPermissions = {
      hidden_page: {
        comp_a: false,
        comp_b: false
      }
    }
    mockGet.mockResolvedValue(hiddenPermissions)
    await initPermissionBus(5)

    expect(canAccessPage('hidden_page', 5)).toBe(false)
  })

  it('未缓存的 level 不可访问', () => {
    expect(canAccessPage('home', 99)).toBe(false)
  })

  it('不存在的页面不可访问', async () => {
    mockGet.mockResolvedValue(mockPermissions)
    await initPermissionBus(5)

    expect(canAccessPage('nonexistent', 5)).toBe(false)
  })
})

describe('usePermission', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    clearPermissionCache()
  })

  it('可见组件应返回 true', async () => {
    mockGet.mockResolvedValue(mockPermissions)
    await initPermissionBus(5)

    const visible = usePermission('home', 'post_card', 5)
    expect(visible.value).toBe(true)
  })

  it('不可见组件应返回 false', async () => {
    mockGet.mockResolvedValue(mockPermissions)
    await initPermissionBus(5)

    const visible = usePermission('home', 'sidebar', 5)
    expect(visible.value).toBe(false)
  })

  it('未缓存的 level 应返回 false', () => {
    const visible = usePermission('home', 'post_card', 99)
    expect(visible.value).toBe(false)
  })

  it('不存在的组件应返回 false', async () => {
    mockGet.mockResolvedValue(mockPermissions)
    await initPermissionBus(5)

    const visible = usePermission('home', 'nonexistent_component', 5)
    expect(visible.value).toBe(false)
  })
})

describe('getVisiblePages', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    clearPermissionCache()
  })

  it('应返回有可见组件的页面列表', async () => {
    mockGet.mockResolvedValue(mockPermissions)
    await initPermissionBus(5)

    const pages = getVisiblePages(5)
    expect(pages).toContain('home')
    expect(pages).toContain('admin_users')
    // admin_settings 所有组件都不可见，不应出现
    expect(pages).not.toContain('admin_settings')
  })

  it('未缓存的 level 应返回空数组', () => {
    expect(getVisiblePages(99)).toEqual([])
  })

  it('所有页面都隐藏时应返回空数组', async () => {
    mockGet.mockResolvedValue({
      page_a: { comp: false },
      page_b: { comp: false }
    })
    await initPermissionBus(5)

    expect(getVisiblePages(5)).toEqual([])
  })
})

describe('clearPermissionCache', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    clearPermissionCache()
  })

  it('清空后应重新拉取', async () => {
    mockGet.mockResolvedValue(mockPermissions)
    await initPermissionBus(5)
    clearPermissionCache()

    mockGet.mockClear()
    mockGet.mockResolvedValue(mockPermissions)

    await getPagePermissions('home', 5)
    expect(mockGet).toHaveBeenCalledTimes(1) // 清空后重新拉取
  })

  it('清空后 canAccessPage 应返回 false', async () => {
    mockGet.mockResolvedValue(mockPermissions)
    await initPermissionBus(5)
    clearPermissionCache()

    expect(canAccessPage('home', 5)).toBe(false)
  })
})