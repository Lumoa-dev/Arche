import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { UserInfo } from '@/components/logic/api/auth'
import {
  loginApi,
  logoutApi,
  refreshTokenApi,
  getUserInfoApi,
  type LoginParams
} from '@/components/logic/api/auth'
import { usePermissionStore } from '@/lib/store/modules/permission'
import { authMockData } from '@/lib/services/mock'

export const useUserStore = defineStore(
  'user',
  () => {
    // token
    const token = ref<string | null>(localStorage.getItem('token'))
    // refresh_token
    const refreshToken = ref<string | null>(localStorage.getItem('refresh_token'))
    // 用户信息
    const userInfo = ref<UserInfo | null>(null)
    // 登录状态
    const isLoggedIn = computed(() => !!token.value && !!userInfo.value)

    const applyUserSession = (
      nextToken: string,
      nextUserInfo: UserInfo,
      nextRefreshToken?: string
    ) => {
      const permissionStore = usePermissionStore()
      const userLevel = nextUserInfo.level ?? 5
      const normalizedPermissions =
        (nextUserInfo.permissions?.length ?? 0) > 0
          ? nextUserInfo.permissions!
          : userLevel === 0
            ? ['*']
            : []

      token.value = nextToken
      refreshToken.value = nextRefreshToken || null
      userInfo.value = nextUserInfo
      permissionStore.setUserPermission(normalizedPermissions, userLevel)

      localStorage.setItem('token', nextToken)
      if (nextRefreshToken) {
        localStorage.setItem('refresh_token', nextRefreshToken)
      }
      localStorage.setItem(
        'userInfo',
        JSON.stringify({
          ...nextUserInfo,
          permissions: normalizedPermissions
        })
      )
    }

    // 真实登录入口，后续页面接账号密码时仍走同一条身份链路
    const login = async (params: LoginParams) => {
      const res = await loginApi(params)
      if (!res.token) {
        throw new Error('登录返回缺少 token')
      }
      applyUserSession(res.token, res.userInfo, res.refresh_token)
      return res
    }

    // 演示模式登录（仅开发环境 mock）
    const loginAsRole = async (role: 'user' | 'admin' | 'guest') => {
      const mockUser = authMockData.users[role]
      if (!mockUser) {
        throw new Error(`未知的演示角色: ${role}`)
      }
      const res = {
        token: `mock-token-${role}-${Date.now()}`,
        userInfo: mockUser as unknown as UserInfo
      }

      applyUserSession(res.token, res.userInfo)
      return res
    }

    // 登出
    const logout = async () => {
      try {
        await logoutApi()
      } finally {
        // 无论接口是否调用成功，都清除本地状态
        clearUserState()
      }
    }

    // 获取用户信息
    const getUserInfo = async () => {
      const res = await getUserInfoApi()
      userInfo.value = res as UserInfo
      localStorage.setItem('userInfo', JSON.stringify(res))
      usePermissionStore().setUserPermission(res.permissions, res.level ?? 5)
      return res
    }

    // 刷新 access_token（使用 refresh_token）
    const refreshAccessToken = async (): Promise<string | null> => {
      const savedRefreshToken = refreshToken.value || localStorage.getItem('refresh_token')
      if (!savedRefreshToken) return null
      try {
        const res = await refreshTokenApi(savedRefreshToken)
        const newToken = res.access_token
        if (newToken) {
          token.value = newToken
          localStorage.setItem('token', newToken)
          return newToken
        }
        return null
      } catch {
        return null
      }
    }

    // 清除用户状态
    const clearUserState = () => {
      token.value = null
      refreshToken.value = null
      userInfo.value = null
      localStorage.removeItem('token')
      localStorage.removeItem('refresh_token')
      localStorage.removeItem('userInfo')
      usePermissionStore().resetPermission()
    }

    const resetState = () => {
      clearUserState()
    }

    // 解码 JWT payload 获取 exp 时间戳（秒）
    const getJwtExp = (rawToken: string): number | null => {
      try {
        const parts = rawToken.split('.')
        if (parts.length !== 3) return null // 不是合法 JWT（可能是 mock-token）
        const payload = JSON.parse(atob(parts[1]!))
        return payload.exp || null
      } catch {
        return null
      }
    }

    // 初始化用户状态，从localStorage恢复
    const initUserState = () => {
      const savedToken = localStorage.getItem('token')
      const savedRefreshToken = localStorage.getItem('refresh_token')
      const savedUserInfo = localStorage.getItem('userInfo')

      if (!savedToken) {
        // 没有 token，清除所有残留状态
        clearUserState()
        return
      }

      // token 有效性预检：如果是合法 JWT 且已过期，且没有 refresh_token，则清除状态
      const exp = getJwtExp(savedToken)
      if (exp !== null) {
        const now = Math.floor(Date.now() / 1000)
        if (now >= exp && !savedRefreshToken) {
          clearUserState()
          return
        }
      }

      token.value = savedToken
      if (savedRefreshToken) {
        refreshToken.value = savedRefreshToken
      }
      if (savedUserInfo) {
        try {
          const parsedUserInfo = JSON.parse(savedUserInfo) as UserInfo
          userInfo.value = parsedUserInfo
          usePermissionStore().setUserPermission(
            parsedUserInfo.permissions,
            parsedUserInfo.level ?? 5
          )
        } catch (e) {
          console.error('解析用户信息失败:', e)
          localStorage.removeItem('userInfo')
        }
      }
    }

    return {
      token,
      refreshToken,
      userInfo,
      isLoggedIn,
      login,
      loginAsRole,
      logout,
      getUserInfo,
      refreshAccessToken,
      clearUserState,
      resetState,
      initUserState
    }
  },
  {
    persist: false // 这里我们自己处理持久化，不需要插件
  }
)
