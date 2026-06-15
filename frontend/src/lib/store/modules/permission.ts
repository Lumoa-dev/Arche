import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { RouteRecordRaw } from 'vue-router'
import {
  canAccessPage as busCanAccessPage,
  initPermissionBus,
  clearPermissionCache,
  getVisiblePages
} from '@/lib/services/permission-bus'

export const usePermissionStore = defineStore(
  'permission',
  () => {
    const routes = ref<RouteRecordRaw[]>([])
    const level = ref<number>(5) // P0=最高, P5=最低
    const routesLoaded = ref(false)

    const whiteList = ['/login', '/404', '/403']

    // 是否为管理员（level 0）
    const isAdmin = () => level.value === 0

    // P等级检查：等级数字越小权限越高
    const hasLevel = (requiredLevel: number): boolean => level.value <= requiredLevel

    // 委托给权限总线：判断页面是否可访问
    const canAccessPage = (pageName: string): boolean => {
      return busCanAccessPage(pageName, level.value)
    }

    // 获取当前 level 所有可见页面列表（用于动态菜单）
    const getVisiblePageList = (): string[] => {
      return getVisiblePages(level.value)
    }

    const setUserPermission = async (_perms: string[] = [], userLevel = 5) => {
      level.value = userLevel
      // 初始化权限总线：从后端拉取页面组件映射
      try {
        await initPermissionBus(userLevel)
      } catch {
        // 拉取失败时保持上次缓存，不影响已有页面渲染
        console.warn('[PermissionBus] 初始化权限数据失败，使用缓存（如有）')
      }
    }

    const resetPermission = () => {
      routes.value = []
      level.value = 5
      routesLoaded.value = false
      clearPermissionCache()
    }

    const resetState = () => {
      resetPermission()
    }

    return {
      routes,
      level,
      routesLoaded,
      whiteList,
      isAdmin,
      hasLevel,
      canAccessPage,
      getVisiblePageList,
      setUserPermission,
      resetPermission,
      resetState
    }
  },
  {
    persist: false
  }
)
