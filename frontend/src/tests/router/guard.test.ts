import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

// 模拟权限总线
vi.mock('@/lib/services/permission-bus', () => ({
  initPermissionBus: vi.fn(() => Promise.resolve()),
  clearPermissionCache: vi.fn(),
  canAccessPage: vi.fn(() => true),
  getVisiblePages: vi.fn(() => [])
}))

// ===== 在 hoisted 作用域中创建所有 mock 工厂和可变状态 =====
const helper = vi.hoisted(() => {
  // 拦截器数组，用于捕获 router.beforeEach / afterEach 注册的 handler
  const capturedBeforeEach: Array<Function> = []
  const capturedAfterEach: Array<Function> = []

  // 可变状态 —— 通过 getter/setter 让 mock store 始终读取最新值
  let _token: string | null = null
  let _userInfo: any = null
  let _isAdmin = false
  let _level = 5
  let _canAccessPage = true

  return {
    capturedBeforeEach,
    capturedAfterEach,

    // 共享状态控制
    setToken: (v: string | null) => {
      _token = v
    },
    setUserInfo: (v: any) => {
      _userInfo = v
    },
    setIsAdmin: (v: boolean) => {
      _isAdmin = v
    },
    setLevel: (v: number) => {
      _level = v
    },
    setCanAccessPage: (v: boolean) => {
      _canAccessPage = v
    },

    // mock 函数（可被 spy/mocked 追踪）
    mockRouterPush: vi.fn(),
    mockInitUserState: vi.fn(),
    mockGetUserInfo: vi.fn().mockRejectedValue(new Error('not initialized')),
    mockRefreshAccessToken: vi.fn().mockRejectedValue(new Error('no token')),
    mockClearUserState: vi.fn(() => {
      _token = null
      _userInfo = null
    }),
    mockResetPermission: vi.fn(),
    mockHasLevel: vi.fn(),
    mockCanAccessPage: vi.fn(() => true),
    mockResetAllStores: vi.fn(),
    mockMessageError: vi.fn(),
    mockCancelAllPendingRequests: vi.fn(),
    mockIsAdmin: vi.fn(),

    // 供 mock factory 使用的 getter
    getToken: () => _token,
    getUserInfo: () => _userInfo,
    getIsAdmin: () => _isAdmin,
    getLevel: () => _level,
    getCanAccessPage: () => _canAccessPage
  }
})

// ===== Mock 所有依赖 =====
vi.mock('@/lib/store/modules/user', () => ({
  useUserStore: vi.fn(() => ({
    get token() {
      return helper.getToken()
    },
    get userInfo() {
      return helper.getUserInfo()
    },
    initUserState: helper.mockInitUserState,
    getUserInfo: helper.mockGetUserInfo,
    refreshAccessToken: helper.mockRefreshAccessToken,
    clearUserState: helper.mockClearUserState
  }))
}))

vi.mock('@/lib/store/modules/permission', () => ({
  usePermissionStore: vi.fn(() => ({
    whiteList: ['/login', '/404', '/403'],
    get level() {
      return helper.getLevel()
    },
    isAdmin: helper.mockIsAdmin,
    hasLevel: helper.mockHasLevel,
    canAccessPage: helper.mockCanAccessPage,
    resetPermission: helper.mockResetPermission
  }))
}))

vi.mock('@/lib/store', () => ({
  resetAllStores: helper.mockResetAllStores
}))

vi.mock('@/lib/utils/message', () => ({
  $message: { error: (...args: any[]) => helper.mockMessageError(...args) }
}))

vi.mock('@/lib/services/request', () => ({
  cancelAllPendingRequests: helper.mockCancelAllPendingRequests
}))

vi.mock('@/lib/constants/auth', () => ({
  AUTH_UNAUTHORIZED_EVENT: 'auth:unauthorized'
}))

vi.mock('@/lib/router/index', () => ({
  default: {
    currentRoute: { value: { path: '/', meta: {}, fullPath: '/' } },
    push: helper.mockRouterPush,
    beforeEach: (fn: Function) => {
      helper.capturedBeforeEach.push(fn)
    },
    afterEach: (fn: Function) => {
      helper.capturedAfterEach.push(fn)
    }
  }
}))

// ===== 导入 guard.ts —— 触发模块级代码（注册事件监听和路由守卫）=====
await import('@/lib/router/guard')

// 创建一个辅助函数用于调用 beforeEach 守卫
function runGuard(to: any, from: any = { path: '/', meta: {} }): Promise<any> {
  return new Promise((resolve) => {
    const handler = helper.capturedBeforeEach[0]!
    handler(to, from, (redirect?: any) => {
      resolve(redirect ?? undefined)
    })
  })
}

describe('路由导航守卫', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // 默认状态：未登录
    helper.setToken(null)
    helper.setUserInfo(null)
    helper.setIsAdmin(false)
    helper.setLevel(5)
    helper.setCanAccessPage(true)
    helper.mockGetUserInfo = vi.fn().mockRejectedValue(new Error('not initialized'))
    helper.mockRefreshAccessToken = vi.fn().mockRejectedValue(new Error('no token'))
  })

  afterEach(() => {
    // 清理事件监听，避免跨测试干扰
    window.dispatchEvent(new CustomEvent('auth:unauthorized'))
  })

  describe('公开页面访问', () => {
    it('白名单页面（/login）允许匿名访问', async () => {
      const result = await runGuard({
        path: '/login',
        meta: { requiresAuth: false },
        fullPath: '/login'
      })
      expect(result).toBeUndefined()
    })

    it('meta.requiresAuth=false 允许匿名访问', async () => {
      const result = await runGuard({ path: '/', meta: { requiresAuth: false }, fullPath: '/' })
      expect(result).toBeUndefined()
    })
  })

  describe('未登录重定向', () => {
    it('没有 token 且不是公开页面，重定向到 /login', async () => {
      // token 默认为 null
      const result = await runGuard({ path: '/profile', meta: {}, fullPath: '/profile' })
      expect(result).toMatchObject({ path: '/login' })
    })

    it('重定向时携带 redirect 参数', async () => {
      const result = await runGuard(
        { path: '/profile', meta: {}, fullPath: '/profile' },
        { path: '/somewhere', meta: {} }
      )
      expect(result).toMatchObject({ path: '/login', query: { redirect: '/profile' } })
    })
  })

  describe('token 过期刷新', () => {
    it('token 未过期时跳过刷新流程', async () => {
      // 构造一个未过期的 JWT（exp 在未来 1 小时）
      const futureExp = Math.floor(Date.now() / 1000) + 3600
      const payload = btoa(JSON.stringify({ exp: futureExp }))
      const mockToken = `header.${payload}.signature`
      helper.setToken(mockToken)
      helper.setUserInfo({ id: '1', username: 'test', level: 5 })
      helper.mockGetUserInfo = vi.fn().mockResolvedValue({ id: '1', username: 'test' })

      const result = await runGuard({ path: '/profile', meta: {}, fullPath: '/profile' })
      expect(result).toBeUndefined()
      expect(helper.mockRefreshAccessToken).not.toHaveBeenCalled()
    })

    it('token 已过期时尝试刷新，刷新成功则继续', async () => {
      const pastExp = Math.floor(Date.now() / 1000) - 60
      const payload = btoa(JSON.stringify({ exp: pastExp }))
      const mockToken = `header.${payload}.signature`
      helper.setToken(mockToken)
      helper.mockRefreshAccessToken = vi.fn().mockResolvedValue('new-token')
      helper.mockGetUserInfo = vi.fn().mockResolvedValue({ id: '1', username: 'test' })
      helper.setUserInfo({ id: '1', username: 'test' })

      const result = await runGuard({ path: '/profile', meta: {}, fullPath: '/profile' })
      expect(result).toBeUndefined()
      expect(helper.mockRefreshAccessToken).toHaveBeenCalled()
    })

    it('token 过期刷新失败时重定向到 /login', async () => {
      const pastExp = Math.floor(Date.now() / 1000) - 60
      const payload = btoa(JSON.stringify({ exp: pastExp }))
      const mockToken = `header.${payload}.signature`
      helper.setToken(mockToken)
      helper.mockRefreshAccessToken = vi.fn().mockResolvedValue(null)

      const result = await runGuard({ path: '/profile', meta: {}, fullPath: '/profile' })
      expect(result).toMatchObject({ path: '/login' })
      expect(helper.mockMessageError).toHaveBeenCalledWith('登录已过期，请重新登录')
    })
  })

  describe('用户信息获取', () => {
    it('没有 userInfo 时自动获取用户信息', async () => {
      helper.setToken('valid-token')
      helper.setUserInfo(null)
      helper.mockGetUserInfo = vi.fn().mockResolvedValue({ id: '1', username: 'test', level: 5 })

      const result = await runGuard({ path: '/profile', meta: {}, fullPath: '/profile' })
      expect(result).toBeUndefined()
      expect(helper.mockGetUserInfo).toHaveBeenCalled()
    })

    it('获取用户信息失败时重定向到 /login', async () => {
      helper.setToken('valid-token')
      helper.setUserInfo(null)
      helper.mockGetUserInfo = vi.fn().mockRejectedValue(new Error('token expired'))

      const result = await runGuard({ path: '/profile', meta: {}, fullPath: '/profile' })
      expect(result).toMatchObject({ path: '/login' })
      expect(helper.mockMessageError).toHaveBeenCalledWith('登录已过期，请重新登录')
    })
  })

  describe('页面权限校验', () => {
    it('to.meta.pageName 不满足时重定向到 /403', async () => {
      helper.setToken('valid-token')
      helper.setUserInfo({ id: '1', username: 'test', level: 5 })
      helper.mockGetUserInfo = vi.fn().mockResolvedValue({ id: '1', username: 'test' })
      helper.mockCanAccessPage = vi.fn(() => false)

      const result = await runGuard({
        path: '/admin/ops/system',
        meta: { pageName: 'admin_ops' },
        fullPath: '/admin/ops/system'
      })
      expect(result).toMatchObject({ path: '/403' })
    })

    it('to.meta.pageName 满足时放行', async () => {
      helper.setToken('valid-token')
      helper.setUserInfo({ id: '1', username: 'test', level: 5 })
      helper.mockGetUserInfo = vi.fn().mockResolvedValue({ id: '1', username: 'test' })
      helper.mockCanAccessPage = vi.fn(() => true)

      const result = await runGuard({
        path: '/profile',
        meta: { pageName: 'profile' },
        fullPath: '/profile'
      })
      expect(result).toBeUndefined()
    })

    it('无 pageName 的页面直接放行', async () => {
      helper.setToken('valid-token')
      helper.setUserInfo({ id: '1', username: 'test', level: 5 })
      helper.mockGetUserInfo = vi.fn().mockResolvedValue({ id: '1', username: 'test' })

      const result = await runGuard({
        path: '/some-page',
        meta: {},
        fullPath: '/some-page'
      })
      expect(result).toBeUndefined()
    })
  })

  describe('level 等级校验', () => {
    it('to.meta.level 不满足时重定向到 /403', async () => {
      helper.setToken('valid-token')
      helper.setUserInfo({ id: '1', username: 'test', level: 5 })
      helper.mockGetUserInfo = vi.fn().mockResolvedValue({ id: '1', username: 'test' })
      helper.mockHasLevel = vi.fn(() => false)

      const result = await runGuard({
        path: '/admin',
        meta: { level: 0 },
        fullPath: '/admin'
      })
      expect(result).toMatchObject({ path: '/403' })
    })

    it('to.meta.level 满足时放行', async () => {
      helper.setToken('valid-token')
      helper.setUserInfo({ id: '1', username: 'test', level: 5 })
      helper.mockGetUserInfo = vi.fn().mockResolvedValue({ id: '1', username: 'test' })
      helper.mockHasLevel = vi.fn(() => true)

      const result = await runGuard({
        path: '/profile',
        meta: { level: 5 },
        fullPath: '/profile'
      })
      expect(result).toBeUndefined()
    })
  })

  describe('afterEach', () => {
    it('设置页面标题', () => {
      const handler = helper.capturedAfterEach[0]!
      handler({ meta: { title: '测试页面' } })
      expect(document.title).toBe('测试页面')
    })

    it('无 title 时使用默认标题', () => {
      const handler = helper.capturedAfterEach[0]!
      handler({ meta: {} })
      expect(document.title).toBe('Arche')
    })
  })

  describe('unauthorized 事件', () => {
    it('触发 auth:unauthorized 事件时重置所有 store', () => {
      window.dispatchEvent(new CustomEvent('auth:unauthorized'))
      expect(helper.mockResetAllStores).toHaveBeenCalled()
    })
  })

  describe('cancelAllPendingRequests', () => {
    it('路由切换时取消待处理请求', async () => {
      helper.setToken('valid-token')
      helper.setUserInfo({ id: '1', username: 'test', level: 5 })
      helper.mockGetUserInfo = vi.fn().mockResolvedValue({ id: '1', username: 'test' })
      helper.mockHasLevel = vi.fn(() => true)

      await runGuard(
        { path: '/profile', meta: {}, fullPath: '/profile' },
        { path: '/previous', meta: {} }
      )
      expect(helper.mockCancelAllPendingRequests).toHaveBeenCalled()
    })

    it('相同路径不取消请求', async () => {
      helper.setToken('valid-token')
      helper.setUserInfo({ id: '1', username: 'test', level: 5 })
      helper.mockGetUserInfo = vi.fn().mockResolvedValue({ id: '1', username: 'test' })
      helper.mockHasLevel = vi.fn(() => true)

      await runGuard({ path: '/same', meta: {}, fullPath: '/same' }, { path: '/same', meta: {} })
      expect(helper.mockCancelAllPendingRequests).not.toHaveBeenCalled()
    })
  })
})
