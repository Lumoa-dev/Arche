/**
 * user store 集成测试。
 *
 * 测什么：真实的 Pinia Store + Mock API → Store 状态联动
 * Mock 边界：@/services/api/auth（API 层）
 * 不 mock：store 本身、permission store、localStorage
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useUserStore } from '@/lib/store/modules/user'

// ── Mock API 层 ──
const { mockLoginApi, mockLogoutApi, mockGetUserInfoApi, mockRefreshTokenApi } = vi.hoisted(() => ({
  mockLoginApi: vi.fn(),
  mockLogoutApi: vi.fn(),
  mockGetUserInfoApi: vi.fn(),
  mockRefreshTokenApi: vi.fn()
}))

vi.mock('@/services/api/auth', () => ({
  loginApi: mockLoginApi,
  logoutApi: mockLogoutApi,
  getUserInfoApi: mockGetUserInfoApi,
  refreshTokenApi: mockRefreshTokenApi
}))

// 模拟 localStorage
const store: Record<string, string> = {}
const mockLocalStorage = {
  getItem: vi.fn((key: string) => store[key] ?? null),
  setItem: vi.fn((key: string, value: string) => {
    store[key] = value
  }),
  removeItem: vi.fn((key: string) => {
    delete store[key]
  }),
  clear: vi.fn(() => {
    Object.keys(store).forEach((k) => delete store[k])
  }),
  get length() {
    return Object.keys(store).length
  },
  key: vi.fn((i: number) => Object.keys(store)[i] ?? null)
}
Object.defineProperty(window, 'localStorage', {
  value: mockLocalStorage,
  configurable: true,
  writable: true
})

describe('user store 集成测试', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    Object.keys(store).forEach((k) => delete store[k])
  })

  describe('login', () => {
    it('登录成功后更新 token / userInfo / permission store', async () => {
      mockLoginApi.mockResolvedValue({
        token: 'access-token-123',
        refresh_token: 'refresh-token-456',
        userInfo: {
          id: '1',
          username: 'testuser',
          email: 'test@example.com',
          level: 5,
          permissions: []
        }
      })

      const userStore = useUserStore()
      const result = await userStore.login({ identity: 'testuser', password: 'testpass' })

      expect(result.token).toBe('access-token-123')
      expect(userStore.token).toBe('access-token-123')
      expect(userStore.refreshToken).toBe('refresh-token-456')
      expect(userStore.userInfo).toBeTruthy()
      expect(userStore.userInfo!.username).toBe('testuser')
      expect(userStore.isLoggedIn).toBe(true)

      // localStorage 同步写入
      expect(store.token).toBe('access-token-123')
      expect(store.refresh_token).toBe('refresh-token-456')
    })

    it('登录返回缺少 token 时抛异常', async () => {
      mockLoginApi.mockResolvedValue({
        token: null,
        userInfo: {
          id: '1',
          username: 'testuser',
          email: 'test@example.com',
          level: 5,
          permissions: []
        }
      })

      const userStore = useUserStore()
      await expect(userStore.login({ identity: 'testuser', password: 'testpass' })).rejects.toThrow(
        '登录返回缺少 token'
      )
      expect(userStore.isLoggedIn).toBe(false)
    })

    it('登录失败时 API 抛异常应透传', async () => {
      mockLoginApi.mockRejectedValue(new Error('用户名或密码错误'))

      const userStore = useUserStore()
      await expect(userStore.login({ identity: 'testuser', password: 'wrong' })).rejects.toThrow(
        '用户名或密码错误'
      )
      expect(userStore.isLoggedIn).toBe(false)
    })
  })

  describe('getUserInfo', () => {
    it('获取用户信息后更新 store', async () => {
      store.token = 'valid-token'
      const userStore = useUserStore()
      userStore.token = 'valid-token'

      const userData = {
        id: '1',
        username: 'testuser',
        email: 'test@example.com',
        level: 3,
        permissions: ['blog:create']
      }
      mockGetUserInfoApi.mockResolvedValue(userData)

      await userStore.getUserInfo()

      expect(userStore.userInfo).toEqual(userData)
      expect(store.userInfo).toBeTruthy()
      expect(JSON.parse(store.userInfo!).username).toBe('testuser')
    })
  })

  describe('logout', () => {
    it('登出时调用 API 并清除状态', async () => {
      store.token = 'valid-token'
      const userStore = useUserStore()
      userStore.token = 'valid-token'
      userStore.userInfo = {
        id: '1',
        username: 'testuser',
        nickname: 'testuser',
        email: 'test@example.com',
        level: 5,
        permissions: []
      }

      mockLogoutApi.mockResolvedValue({})

      await userStore.logout()

      expect(mockLogoutApi).toHaveBeenCalledOnce()
      expect(userStore.token).toBeNull()
      expect(userStore.userInfo).toBeNull()
      expect(userStore.isLoggedIn).toBe(false)
    })

    it('API 失败时仍然清除状态', async () => {
      store.token = 'valid-token'
      const userStore = useUserStore()
      userStore.token = 'valid-token'
      userStore.userInfo = {
        id: '1',
        username: 'testuser',
        nickname: 'testuser',
        email: 'test@example.com',
        level: 5,
        permissions: []
      }

      mockLogoutApi.mockRejectedValue(new Error('网络错误'))

      // logout 的 finally 块会清理状态，但异常继续抛出
      await expect(userStore.logout()).rejects.toThrow('网络错误')

      // 即使 API 失败，本地状态也清除了
      expect(userStore.token).toBeNull()
      expect(userStore.userInfo).toBeNull()
    })
  })

  describe('refreshAccessToken', () => {
    it('使用 refresh_token 获取新 access_token', async () => {
      store.refresh_token = 'saved-refresh'
      const userStore = useUserStore()
      userStore.refreshToken = 'saved-refresh'

      mockRefreshTokenApi.mockResolvedValue({ access_token: 'new-access-token' })

      const newToken = await userStore.refreshAccessToken()

      expect(newToken).toBe('new-access-token')
      expect(userStore.token).toBe('new-access-token')
      expect(store.token).toBe('new-access-token')
    })

    it('无 refresh_token 时返回 null', async () => {
      const userStore = useUserStore()
      const result = await userStore.refreshAccessToken()
      expect(result).toBeNull()
    })

    it('API 失败时返回 null', async () => {
      store.refresh_token = 'expired-refresh'
      const userStore = useUserStore()
      userStore.refreshToken = 'expired-refresh'

      mockRefreshTokenApi.mockRejectedValue(new Error('refresh token expired'))

      const result = await userStore.refreshAccessToken()
      expect(result).toBeNull()
    })
  })

  describe('initUserState', () => {
    it('有完整 localStorage 时恢复状态', () => {
      store.token = 'stored-token'
      store.refresh_token = 'stored-refresh'
      store.userInfo = JSON.stringify({
        id: '1',
        username: 'testuser',
        email: 'test@example.com',
        level: 5,
        permissions: []
      })

      const userStore = useUserStore()
      userStore.initUserState()

      expect(userStore.token).toBe('stored-token')
      expect(userStore.refreshToken).toBe('stored-refresh')
      expect(userStore.userInfo).toBeTruthy()
      expect(userStore.userInfo!.username).toBe('testuser')
    })

    it('无 token 时清除所有状态', () => {
      store.userInfo = JSON.stringify({
        id: '1',
        username: 'testuser',
        email: 'test@example.com',
        level: 5,
        permissions: []
      })

      const userStore = useUserStore()
      userStore.initUserState()

      expect(userStore.token).toBeNull()
      expect(userStore.userInfo).toBeNull()
    })

    it('JWT 过期且无 refresh_token 时清除状态', () => {
      // 创建一个过期的 JWT
      const expiredPayload = btoa(JSON.stringify({ exp: Math.floor(Date.now() / 1000) - 3600 }))
      store.token = `header.${expiredPayload}.signature`

      const userStore = useUserStore()
      userStore.initUserState()

      expect(userStore.token).toBeNull()
    })

    it('JWT 过期但有 refresh_token 时保留 token', () => {
      const expiredPayload = btoa(JSON.stringify({ exp: Math.floor(Date.now() / 1000) - 3600 }))
      store.token = `header.${expiredPayload}.signature`
      store.refresh_token = 'still-valid-refresh'

      const userStore = useUserStore()
      userStore.initUserState()

      // token 保留，等 refreshAccessToken 尝试刷新
      expect(userStore.token).toBeTruthy()
      expect(userStore.refreshToken).toBe('still-valid-refresh')
    })
  })
})
