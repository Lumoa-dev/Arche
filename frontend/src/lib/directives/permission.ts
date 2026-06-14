import type { App, DirectiveBinding } from 'vue'
import { usePermissionStore } from '@/lib/store/modules/permission'

export const permissionDirective = {
  mounted(el: HTMLElement, binding: DirectiveBinding<string | string[]>) {
    const permissionStore = usePermissionStore()
    const { value } = binding

    // admin（level 0）拥有所有权限
    if (permissionStore.isAdmin()) {
      return
    }

    // 如果没有传入权限，默认显示
    if (!value) {
      return
    }

    let hasPermission = false

    if (typeof value === 'string') {
      hasPermission = permissionStore.hasPermission(value)
    } else if (Array.isArray(value)) {
      // 只要有一个权限满足就显示
      hasPermission = value.some((perm) => permissionStore.hasPermission(perm))
    }

    // 如果没有权限，移除元素
    if (!hasPermission) {
      el.parentNode?.removeChild(el)
    }
  }
}

export function setupPermissionDirective(app: App) {
  app.directive('permission', permissionDirective)
}
