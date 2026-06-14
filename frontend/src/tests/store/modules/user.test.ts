import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useUserStore } from '@/lib/store/modules/user'
import { usePermissionStore } from '@/lib/store/modules/permission'
import type { UserInfo } from '@/components/logic/api/auth'

// 模拟 auth API
vi.mock('@/services/api/auth', () => ({
  loginApi: vi.fn(),
  logoutApi: vi.fn(),
  refreshTokenApi: vi.fn(),
  getUserInfoApi: vi.fn()
}))

import { loginApi, logoutApi, refreshTokenApi, getUserInfoApi } from '@/components/logic/api/auth'

describe('useUserStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
  })

  describe('初始状态', () => {
    it('token 默认为 null', () => {
      const store = useUserStore()
      expect(store.token).toBeNull()
    })

    it('refreshToken 默认为 null', () => {
      const store = useUserStore()
      expect(store.refreshToken).toBeNull()
    })

    it('userInfo 默认为 null', () => {
      const store = useUserStore()
      expect(store.userInfo).toBeNull()
    })

    it('isLoggedIn 为 false', () => {
      const store = useUserStore()
      expect(store.isLoggedIn).toBe(false)
    })
  })

  describe('isLoggedIn', () => {
    it('有 token 和 userInfo 时为 true', () => {
      const store = useUserStore()
      store.token = 'mock-token'
      store.userInfo = {
        id: '1',
        username: 'test',
        nickname: 'Test',
        email: 'test@test.com',
        level: 5,
        permissions: []
      }
      expect(store.isLoggedIn).toBe(true)
    })

    it('仅有 token 没有 userInfo 时为 false', () => {
      const store = useUserStore()
      store.token = 'mock-token'
      expect(store.isLoggedIn).toBe(false)
    })
  })

  describe('loginAsRole', () => {
    it('以 user 角色登录成功', async () => {
      const store = useUserStore()
      await store.loginAsRole('user')

      expect(store.token).toContain('mock-token-user')
      expect(store.userInfo).not.toBeNull()
      expect(store.userInfo?.username).toBe('user')
      expect(store.userInfo?.nickname).toBe('普通用户')
      expect(store.isLoggedIn).toBe(true)
    })

    it('以 admin 角色登录成功', async () => {
      const store = useUserStore()
      await store.loginAsRole('admin')

      expect(store.token).toContain('mock-token-admin')
      expect(store.userInfo?.username).toBe('admin')
      expect(store.userInfo?.permissions).toContain('*')
      expect(store.isLoggedIn).toBe(true)
    })

    it('管理员登录后 permission store 状态正确', async () => {
      const store = useUserStore()
      await store.loginAsRole('admin')

      const permissionStore = usePermissionStore()
      expect(permissionStore.isAdmin()).toBe(true)
      expect(permissionStore.hasPermission('anything')).toBe(true)
    })

    it('以 guest 角色登录后 permission 为空', async () => {
      const store = useUserStore()
      await store.loginAsRole('guest')

      const permissionStore = usePermissionStore()
      expect(permissionStore.isAdmin()).toBe(false)
      expect(permissionStore.permissions).toEqual([])
    })

    it('未知角色抛出错误', async () => {
      const store = useUserStore()
      await expect(store.loginAsRole('unknown' as 'user')).rejects.toThrow('未知的演示角色')
    })
  })

  describe('login', () => {
    it('调用 loginApi 并应用用户会话', async () => {
      const mockUserInfo: UserInfo = {
        id: '1',
        username: 'testuser',
        nickname: '测试用户',
        email: 'test@test.com',
        permissions: ['blog:read'],
        level: 5
      }
      vi.mocked(loginApi).mockResolvedValueOnce({
        token: 'real-token',
        userInfo: mockUserInfo,
        refresh_token: 'refresh-token'
      })

      const store = useUserStore()
      const result = await store.login({ identity: 'testuser', password: '123456' })

      expect(loginApi).toHaveBeenCalledWith({ identity: 'testuser', password: '123456' })
      expect(store.token).toBe('real-token')
      expect(store.refreshToken).toBe('refresh-token')
      expect(store.userInfo).toEqual(mockUserInfo)
      expect(store.isLoggedIn).toBe(true)
      expect(result.token).toBe('real-token')
    })

    it('登录返回缺少 token 时抛出错误', async () => {
      vi.mocked(loginApi).mockResolvedValueOnce({
        token: undefined as unknown as string,
        refresh_token: undefined,
        userInfo: {
          id: '1',
          username: 'test',
          nickname: 'Test',
          email: 'test@test.com',
          level: 5,
          permissions: []
        }
      })

      const store = useUserStore()
      await expect(store.login({ identity: 'test', password: '123' })).rejects.toThrow(
        '登录返回缺少 token'
      )
    })
  })

  describe('logout', () => {
    it('调用 logoutApi 并清除本地状态', async () => {
      vi.mocked(logoutApi).mockResolvedValueOnce(undefined)

      // 先登录
      const store = useUserStore()
      store.token = 'mock-token'
      store.userInfo = {
        id: '1',
        username: 'testuser',
        nickname: 'Test',
        email: 'test@test.com',
        level: 5,
        permissions: []
      }
      localStorage.setItem('token', 'mock-token')

      await store.logout()

      expect(logoutApi).toHaveBeenCalled()
      expect(store.token).toBeNull()
      expect(store.userInfo).toBeNull()
      expect(store.isLoggedIn).toBe(false)
    })

    it('logoutApi 失败时仍然清除本地状态', async () => {
      vi.mocked(logoutApi).mockRejectedValueOnce(new Error('Network error'))

      const store = useUserStore()
      store.token = 'mock-token'
      store.userInfo = {
        id: '1',
        username: 'test',
        nickname: 'Test',
        email: 'test@test.com',
        level: 5,
        permissions: []
      }

      // logout 的 try/finally 中 finally 先执行，然后错误继续传播
      await expect(store.logout()).rejects.toThrow('Network error')

      expect(store.token).toBeNull()
      expect(store.userInfo).toBeNull()
    })
  })

  describe('getUserInfo', () => {
    it('获取用户信息并更新状态', async () => {
      const mockUserResponse = {
        id: '1',
        username: 'testuser',
        nickname: '测试用户',
        permissions: ['blog:read', 'blog:write'],
        level: 3
      }
      vi.mocked(getUserInfoApi).mockResolvedValueOnce(mockUserResponse as any)

      const store = useUserStore()
      await store.getUserInfo()

      expect(getUserInfoApi).toHaveBeenCalled()
      expect(store.userInfo?.username).toBe('testuser')
      expect(store.userInfo?.permissions).toEqual(['blog:read', 'blog:write'])

      // 验证同步更新了 permission store
      const permissionStore = usePermissionStore()
      expect(permissionStore.permissions).toEqual(['blog:read', 'blog:write'])
      expect(permissionStore.level).toBe(3)
    })
  })

  describe('refreshAccessToken', () => {
    it('使用 refreshToken 刷新成功', async () => {
      vi.mocked(refreshTokenApi).mockResolvedValueOnce({ access_token: 'new-token' })

      const store = useUserStore()
      store.refreshToken = 'saved-refresh-token'
      const newToken = await store.refreshAccessToken()

      expect(refreshTokenApi).toHaveBeenCalledWith('saved-refresh-token')
      expect(newToken).toBe('new-token')
      expect(store.token).toBe('new-token')
    })

    it('无 refreshToken 时返回 null', async () => {
      const store = useUserStore()
      const result = await store.refreshAccessToken()
      expect(result).toBeNull()
    })

    it('API 调用失败时返回 null', async () => {
      vi.mocked(refreshTokenApi).mockRejectedValueOnce(new Error('Network error'))

      const store = useUserStore()
      store.refreshToken = 'invalid-token'
      const result = await store.refreshAccessToken()

      expect(result).toBeNull()
    })
  })

  describe('clearUserState', () => {
    it('清除 token / userInfo / 本地存储', () => {
      // 先设一些值
      localStorage.setItem('token', 'test-token')
      localStorage.setItem('refresh_token', 'test-refresh')
      localStorage.setItem(
        'userInfo',
        JSON.stringify({ id: '1', username: 'test', nickname: 'Test', permissions: [] })
      )

      const store = useUserStore()
      store.token = 'test-token'
      store.refreshToken = 'test-refresh'
      store.userInfo = {
        id: '1',
        username: 'test',
        nickname: 'Test',
        email: 'test@test.com',
        level: 5,
        permissions: []
      }

      store.clearUserState()

      expect(store.token).toBeNull()
      expect(store.refreshToken).toBeNull()
      expect(store.userInfo).toBeNull()
      expect(localStorage.getItem('token')).toBeNull()
      expect(localStorage.getItem('refresh_token')).toBeNull()
      expect(localStorage.getItem('userInfo')).toBeNull()
    })

    it('清除后 permission store 也被重置', () => {
      const permissionStore = usePermissionStore()
      permissionStore.setUserPermission(['admin'], 0)

      const store = useUserStore()
      store.clearUserState()

      expect(permissionStore.isAdmin()).toBe(false)
      expect(permissionStore.permissions).toEqual([])
      expect(permissionStore.level).toBe(5)
    })
  })

  describe('resetState', () => {
    it('调用 clearUserState 清除所有状态', () => {
      const store = useUserStore()
      store.token = 'test-token'
      store.userInfo = {
        id: '1',
        username: 'test',
        nickname: 'Test',
        email: 'test@test.com',
        level: 5,
        permissions: []
      }

      store.resetState()

      expect(store.token).toBeNull()
      expect(store.userInfo).toBeNull()
    })
  })

  describe('initUserState', () => {
    it('从 localStorage 恢复用户状态', () => {
      const userInfoData = {
        id: '1',
        username: 'test',
        nickname: 'Test',
        permissions: ['blog:read'],
        level: 5
      }
      localStorage.setItem('token', 'saved-token')
      localStorage.setItem('refresh_token', 'saved-refresh')
      localStorage.setItem('userInfo', JSON.stringify(userInfoData))

      const store = useUserStore()
      store.initUserState()

      expect(store.token).toBe('saved-token')
      expect(store.refreshToken).toBe('saved-refresh')
      expect(store.userInfo?.username).toBe('test')
      expect(store.isLoggedIn).toBe(true)
    })

    it('无 token 时清除所有残留状态', () => {
      localStorage.setItem('token', '')
      localStorage.setItem(
        'userInfo',
        JSON.stringify({ id: '1', username: 'test', nickname: 'Test', permissions: [] })
      )

      const store = useUserStore()
      store.token = 'stale-token'
      store.initUserState()

      expect(store.token).toBeNull()
      expect(store.userInfo).toBeNull()
    })

    it('JWT 过期且无 refresh_token 时清除状态', () => {
      // 创建一个已过期的 JWT payload
      const expiredPayload = btoa(JSON.stringify({ exp: Math.floor(Date.now() / 1000) - 3600 }))
      const expiredToken = `header.${expiredPayload}.signature`

      localStorage.setItem('token', expiredToken)

      const store = useUserStore()
      store.initUserState()

      expect(store.token).toBeNull()
    })

    it('JWT 过期但有 refresh_token 时不清除', () => {
      const expiredPayload = btoa(JSON.stringify({ exp: Math.floor(Date.now() / 1000) - 3600 }))
      const expiredToken = `header.${expiredPayload}.signature`

      localStorage.setItem('token', expiredToken)
      localStorage.setItem('refresh_token', 'valid-refresh')

      const store = useUserStore()
      store.initUserState()

      expect(store.token).toBe(expiredToken)
      expect(store.refreshToken).toBe('valid-refresh')
    })
  })

  // getJwtExp 是 store 内部方法（未暴露），JWT 过期逻辑已通过 initUserState 的测试覆盖
})
