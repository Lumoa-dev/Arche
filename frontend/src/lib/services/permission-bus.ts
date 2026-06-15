/**
 * 权限总线 (Permission Bus)
 *
 * 核心机制：前端组件通过总线订阅页面组件可见性，总线从后端运行时拉取权限数据。
 * 后端是唯一事实源，前端零硬编码权限值。
 *
 * 数据结构（后端返回）：
 *   { pageName: { componentName: boolean } }
 *   页面下任一组件 visible → 页面可访问
 *
 * 使用示例：
 *   const canShow = usePermission('home', 'post_card')
 *   if (canAccessPage('admin_users')) { ... }
 */

import { reactive, computed, type ComputedRef } from 'vue'
import { get } from '@/lib/services/request'

// ── 类型 ──

/** 后端返回的页面组件权限映射 */
export interface PagePermissionMap {
  [pageName: string]: {
    [componentName: string]: boolean
  }
}

// ── 状态 ──

/** 全量页面权限映射，按 level 分组缓存 */
const permissionCache = reactive<Record<number, PagePermissionMap>>({})

/** 当前已加载的 level 列表 */
const loadedLevels = reactive<Set<number>>(new Set())

/** 最后拉取时间戳（ms） */
let lastFetchTime = 0

/** TTL：5 分钟 */
const CACHE_TTL_MS = 5 * 60 * 1000

// ── 内部函数 ──

/**
 * 从后端拉取指定 level 的页面权限映射。
 * 后端 URL：GET /api/auth/permissions/pages?level={level}
 */
async function fetchLevelPermissions(level: number): Promise<PagePermissionMap> {
  const res = await get<PagePermissionMap>('/auth/permissions/pages', { level })
  return res
}

/**
 * 检查缓存是否有效（存在且未过期）
 */
function isCacheValid(): boolean {
  return Date.now() - lastFetchTime < CACHE_TTL_MS
}

// ── 公开 API ──

/**
 * 初始化权限总线：拉取并缓存指定 level 的权限数据。
 * 应在用户登录成功或切换到新角色时调用。
 *
 * @param level - 用户等级（0-10）
 */
export async function initPermissionBus(level: number): Promise<void> {
  const map = await fetchLevelPermissions(level)
  permissionCache[level] = map
  loadedLevels.add(level)
  lastFetchTime = Date.now()
}

/**
 * 刷新指定 level 的缓存（强制拉取，忽略 TTL）。
 */
export async function refreshPermissionLevel(level: number): Promise<void> {
  const map = await fetchLevelPermissions(level)
  permissionCache[level] = map
  loadedLevels.add(level)
  lastFetchTime = Date.now()
}

/**
 * 获取指定页面下所有组件的权限映射。
 * 优先使用缓存，缓存过期或不存在时自动拉取。
 *
 * @param pageName - 页面名称
 * @param level - 用户等级（默认取缓存中的任意 level）
 */
export async function getPagePermissions(
  pageName: string,
  level: number
): Promise<{ [componentName: string]: boolean } | null> {
  // 尝试从缓存获取
  const levelCache = permissionCache[level]
  if (levelCache && levelCache[pageName]) {
    return levelCache[pageName]
  }

  // 缓存过期或无数据，尝试拉取
  if (!isCacheValid() || !loadedLevels.has(level)) {
    await initPermissionBus(level)
    const freshCache = permissionCache[level]
    return freshCache?.[pageName] ?? null
  }

  return null
}

/**
 * 订阅单个组件的可见性。
 * 返回 ComputedRef<boolean>，响应式更新。
 *
 * @param pageName - 页面名称
 * @param componentName - 组件名称
 * @param level - 用户等级
 */
export function usePermission(
  pageName: string,
  componentName: string,
  level: number
): ComputedRef<boolean> {
  return computed(() => {
    const levelCache = permissionCache[level]
    if (!levelCache || !levelCache[pageName]) {
      return false
    }
    return levelCache[pageName][componentName] ?? false
  })
}

/**
 * 判断某个页面是否可访问（页面下任一组件 visible）。
 *
 * @param pageName - 页面名称
 * @param level - 用户等级
 */
export function canAccessPage(pageName: string, level: number): boolean {
  const levelCache = permissionCache[level]
  if (!levelCache || !levelCache[pageName]) {
    return false
  }
  const components = levelCache[pageName]
  return Object.values(components).some((visible) => visible === true)
}

/**
 * 获取当前已缓存的所有页面名称（有任一组件可见的页面）。
 * 用于动态渲染侧边栏/导航菜单。
 */
export function getVisiblePages(level: number): string[] {
  const levelCache = permissionCache[level]
  if (!levelCache) {
    return []
  }
  return Object.entries(levelCache)
    .filter(([, components]) => Object.values(components).some((v) => v === true))
    .map(([pageName]) => pageName)
}

/**
 * 清空所有权限缓存。
 */
export function clearPermissionCache(): void {
  Object.keys(permissionCache).forEach((key) => {
    delete permissionCache[Number(key)]
  })
  loadedLevels.clear()
  lastFetchTime = 0
}
