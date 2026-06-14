import router from './index'
import { resetAllStores } from '@/lib/store'
import { useUserStore } from '@/lib/store/modules/user'
import { usePermissionStore } from '@/lib/store/modules/permission'
import { $message } from '@/lib/utils/message'
import { AUTH_UNAUTHORIZED_EVENT } from '@/lib/constants/auth'
import { cancelAllPendingRequests } from '@/lib/services/request'
let routerInitiated = false

const isCurrentRoutePublic = () => {
  const currentRoute = router.currentRoute.value
  if (!currentRoute) {
    return false
  }
  return (
    currentRoute.meta?.requiresAuth === false ||
    usePermissionStore().whiteList.includes(currentRoute.path)
  )
}

const onUnauthorized = () => {
  resetAllStores()

  // 未登录状态下，公开页面允许继续以游客身份浏览，不强制跳转登录。
  if (!isCurrentRoutePublic() && router.currentRoute.value.path !== '/login') {
    router.push('/login')
  }
}

window.addEventListener(AUTH_UNAUTHORIZED_EVENT, onUnauthorized)

const canAccessRoutePermission = (
  permissionStore: ReturnType<typeof usePermissionStore>,
  routePermission: unknown
) => {
  if (!routePermission) {
    return true
  }

  if (typeof routePermission === 'string') {
    return permissionStore.hasPermission(routePermission)
  }

  if (Array.isArray(routePermission)) {
    return routePermission.some((permission) => permissionStore.hasPermission(String(permission)))
  }

  return true
}

// 解码 JWT payload 获取 exp 时间戳（秒）
const getJwtExp = (token: string): number | null => {
  try {
    const parts = token.split('.')
    if (parts.length !== 3) return null // 不是合法 JWT（可能是 mock-token）
    const payload = JSON.parse(atob(parts[1]!))
    return payload.exp || null
  } catch {
    return null
  }
}

router.beforeEach(async (to, from, next) => {
  if (from.path && from.path !== to.path) {
    cancelAllPendingRequests()
  }

  const userStore = useUserStore()
  const permissionStore = usePermissionStore()

  // 初始化用户状态（页面刷新时从localStorage恢复）
  if (!routerInitiated) {
    userStore.initUserState()
    routerInitiated = true
  }

  const token = userStore.token
  // 公开页面（requiresAuth=false）允许匿名访问
  if (to.meta?.requiresAuth === false || permissionStore.whiteList.includes(to.path)) {
    next()
    return
  }

  // 没有token，跳转到登录页
  if (!token) {
    next({ path: '/login', query: { redirect: to.fullPath } })
    return
  }

  // token 过期预检：如果 token 已过期（或 5 分钟内过期），尝试刷新
  const exp = getJwtExp(token)
  if (exp !== null) {
    const now = Math.floor(Date.now() / 1000)
    if (now >= exp - 300) {
      // 过期或即将过期，尝试刷新
      const newToken = await userStore.refreshAccessToken()
      if (!newToken) {
        // 刷新失败，清除状态跳转登录
        $message.error('登录已过期，请重新登录')
        userStore.clearUserState()
        permissionStore.resetPermission()
        next({ path: '/login', query: { redirect: to.fullPath } })
        return
      }
    }
  }

  // 有token，但是用户信息不存在，获取用户信息
  if (!userStore.userInfo) {
    try {
      await userStore.getUserInfo()
    } catch {
      // 获取用户信息失败，说明token过期，跳转到登录页
      $message.error('登录已过期，请重新登录')
      userStore.clearUserState()
      permissionStore.resetPermission()
      next({ path: '/login', query: { redirect: to.fullPath } })
      return
    }
  }

  // 如果权限路由尚未加载，初始化权限状态
  if (!permissionStore.routesLoaded && userStore.userInfo) {
    try {
      // 根据用户角色生成可访问路由列表，admin 路由通过 addRoute 动态注册
      await permissionStore.generateRoutes()
    } catch {
      // 生成路由失败，跳转到首页
      $message.error('获取权限失败，请重新登录')
      next({ path: '/' })
      return
    }
  }

  const requiredPermission = to.meta?.permission
  const requiredLevel = to.meta?.level as number | undefined
  if (requiredLevel !== undefined && !permissionStore.hasLevel(requiredLevel)) {
    next({ path: '/403', query: { redirect: to.fullPath } })
    return
  }
  if (!canAccessRoutePermission(permissionStore, requiredPermission)) {
    next({ path: '/403', query: { redirect: to.fullPath } })
    return
  }

  // 路由存在，正常访问
  next()
})

router.afterEach((to) => {
  // 设置页面标题
  document.title = (to.meta?.title as string) || 'Arche'
})
