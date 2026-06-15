import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { usePermissionStore } from '@/lib/store/modules/permission'
import { permissionDirective, setupPermissionDirective } from '@/lib/directives/permission'

// 模拟权限总线
vi.mock('@/lib/services/permission-bus', () => ({
  initPermissionBus: vi.fn(() => Promise.resolve()),
  clearPermissionCache: vi.fn(),
  canAccessPage: vi.fn(() => true),
  getVisiblePages: vi.fn(() => [])
}))

describe('permission 指令', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('管理员（level 0）显示所有元素，不移除', () => {
    const store = usePermissionStore()
    store.setUserPermission([], 0)

    const el = document.createElement('div')
    const parent = document.createElement('div')
    parent.appendChild(el)
    const removeSpy = vi.spyOn(parent, 'removeChild')

    permissionDirective.mounted(el, {
      value: 'home.post_card',
      instance: null,
      dir: {},
      modifiers: {},
      oldValue: undefined
    } as any)

    expect(removeSpy).not.toHaveBeenCalled()
  })

  it('没有传入权限值时显示元素', () => {
    const store = usePermissionStore()
    store.setUserPermission([], 5)

    const el = document.createElement('div')
    const parent = document.createElement('div')
    parent.appendChild(el)
    const removeSpy = vi.spyOn(parent, 'removeChild')

    permissionDirective.mounted(el, {
      value: undefined,
      instance: null,
      dir: {},
      modifiers: {},
      oldValue: undefined
    } as any)

    expect(removeSpy).not.toHaveBeenCalled()
  })

  it('无点号格式时（旧格式）不移除元素（兼容降级）', () => {
    const store = usePermissionStore()
    store.setUserPermission([], 5)

    const el = document.createElement('div')
    const parent = document.createElement('div')
    parent.appendChild(el)

    permissionDirective.mounted(el, {
      value: 'blog:write',
      instance: null,
      dir: {},
      modifiers: {},
      oldValue: undefined
    } as any)

    // 无点号的旧格式，降级为不阻止显示
    expect(parent.contains(el)).toBe(true)
  })

  it('数组权限：只要有一个满足就显示', () => {
    const store = usePermissionStore()
    store.setUserPermission([], 5)

    const el = document.createElement('div')
    const parent = document.createElement('div')
    parent.appendChild(el)

    permissionDirective.mounted(el, {
      value: ['explore.post_list', 'home.post_card'],
      instance: null,
      dir: {},
      modifiers: {},
      oldValue: undefined
    } as any)

    expect(parent.contains(el)).toBe(true)
  })

  it('setupPermissionDirective 注册 v-permission 指令', () => {
    const app = {
      directive: vi.fn()
    }

    setupPermissionDirective(app as any)

    expect(app.directive).toHaveBeenCalledWith('permission', expect.any(Object))
  })
})
