import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { RouteRecordRaw } from 'vue-router'

export const usePermissionStore = defineStore(
  'permission',
  () => {
    const routes = ref<RouteRecordRaw[]>([])
    const permissions = ref<string[]>([])
    const level = ref<number>(5) // P0=最高, P5=最低
    const routesLoaded = ref(false)

    const whiteList = ['/login', '/404', '/403']

    // 是否为管理员（level 0）
    const isAdmin = () => level.value === 0

    // P等级检查：等级数字越小权限越高
    const hasLevel = (requiredLevel: number): boolean => level.value <= requiredLevel

    const hasPermission = (permission: string): boolean => {
      return (
        level.value === 0 ||
        permissions.value.includes('*') ||
        permissions.value.includes(permission)
      )
    }

    const generateRoutes = async (): Promise<RouteRecordRaw[]> => {
      routesLoaded.value = true
      return []
    }

    const setPermissions = (perms: string[]) => {
      permissions.value = perms
    }

    const setUserPermission = (perms: string[] = [], userLevel = 5) => {
      permissions.value = perms
      level.value = userLevel
    }

    const resetPermission = () => {
      routes.value = []
      permissions.value = []
      level.value = 5
      routesLoaded.value = false
    }

    const resetState = () => {
      resetPermission()
    }

    return {
      routes,
      permissions,
      level,
      routesLoaded,
      whiteList,
      isAdmin,
      hasLevel,
      hasPermission,
      generateRoutes,
      setPermissions,
      setUserPermission,
      resetPermission,
      resetState
    }
  },
  {
    persist: false
  }
)
