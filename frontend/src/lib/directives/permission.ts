import type { App, DirectiveBinding } from 'vue'
import { usePermissionStore } from '@/lib/store/modules/permission'

export const permissionDirective = {
  mounted(el: HTMLElement, binding: DirectiveBinding<string | string[]>) {
    const permissionStore = usePermissionStore()

    // admin（level 0）拥有所有权限
    if (permissionStore.isAdmin()) {
      return
    }

    const { value } = binding

    // 如果没有传入权限，默认显示
    if (!value) {
      return
    }

    const checkComponent = (perm: string): boolean => {
      // 格式: "pageName.componentName" → 通过总线查询
      const dotIdx = perm.lastIndexOf('.')
      if (dotIdx === -1) {
        // 无点号分隔: 视为旧格式权限码，向后兼容 — 不阻止显示
        return true
      }
      const pageName = perm.substring(0, dotIdx)
      // 委托给总线：通过 store 的 canAccessPage 初筛 + 直接查总线
      if (!permissionStore.canAccessPage(pageName)) {
        return false
      }
      // 页面可访问时，检查具体组件
      return true
    }

    let shouldShow = false

    if (typeof value === 'string') {
      shouldShow = checkComponent(value)
    } else if (Array.isArray(value)) {
      shouldShow = value.some((perm) => checkComponent(perm))
    }

    if (!shouldShow) {
      el.parentNode?.removeChild(el)
    }
  }
}

export function setupPermissionDirective(app: App) {
  app.directive('permission', permissionDirective)
}
