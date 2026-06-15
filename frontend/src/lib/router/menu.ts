import type { Component } from 'vue'
import type { RouteRecordRaw } from 'vue-router'
import * as IconSet from '@/icons'

interface RouteMetaLike {
  title?: string
  layout?: string
  icon?: string
  menu?: boolean
}

export interface AppMenuItem {
  title: string
  path: string
  icon?: Component
}

const resolveRoutePath = (parentPath: string, routePath: string) => {
  if (!routePath) {
    return parentPath
  }
  if (routePath.startsWith('/')) {
    return routePath
  }
  const normalizedParent = parentPath.endsWith('/') ? parentPath.slice(0, -1) : parentPath
  return `${normalizedParent}/${routePath}`
}

const readRouteMeta = (route: RouteRecordRaw): RouteMetaLike => {
  return (route.meta || {}) as RouteMetaLike
}

const resolveIcon = (iconName?: string): Component | undefined => {
  if (!iconName) {
    return undefined
  }
  return (IconSet as Record<string, Component>)[iconName]
}

export const buildLayoutMenus = (
  routes: RouteRecordRaw[],
  targetLayout: 'user' | 'admin'
): AppMenuItem[] => {
  const menus: AppMenuItem[] = []

  const visit = (routeList: RouteRecordRaw[], parentPath = '') => {
    routeList.forEach((route) => {
      const meta = readRouteMeta(route)
      const fullPath = resolveRoutePath(parentPath, route.path)

      if (meta.layout === targetLayout && meta.menu !== false && meta.title) {
        const icon = resolveIcon(meta.icon)
        const menuItem: AppMenuItem = {
          title: meta.title,
          path: fullPath
        }
        if (icon) {
          menuItem.icon = icon
        }
        menus.push(menuItem)
      }

      if (route.children?.length) {
        visit(route.children, fullPath)
      }
    })
  }

  visit(routes)
  return menus
}
