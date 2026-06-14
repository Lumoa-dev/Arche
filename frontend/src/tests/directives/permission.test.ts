import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { usePermissionStore } from '@/lib/store/modules/permission'
import { permissionDirective, setupPermissionDirective } from '@/lib/directives/permission'

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
      value: 'some:permission',
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

  it('不具备权限时移除元素', () => {
    const store = usePermissionStore()
    store.setUserPermission(['blog:read'], 5)

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

    expect(parent.contains(el)).toBe(false)
  })

  it('具备权限时不移除元素', () => {
    const store = usePermissionStore()
    store.setUserPermission(['blog:write'], 5)

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

    expect(parent.contains(el)).toBe(true)
  })

  it('数组权限：只要有一个满足就显示', () => {
    const store = usePermissionStore()
    store.setUserPermission(['blog:read'], 5)

    const el = document.createElement('div')
    const parent = document.createElement('div')
    parent.appendChild(el)

    permissionDirective.mounted(el, {
      value: ['blog:write', 'blog:read'],
      instance: null,
      dir: {},
      modifiers: {},
      oldValue: undefined
    } as any)

    expect(parent.contains(el)).toBe(true)
  })

  it('数组权限：没有一个满足时移除', () => {
    const store = usePermissionStore()
    store.setUserPermission(['blog:read'], 5)

    const el = document.createElement('div')
    const parent = document.createElement('div')
    parent.appendChild(el)

    permissionDirective.mounted(el, {
      value: ['blog:write', 'blog:delete'],
      instance: null,
      dir: {},
      modifiers: {},
      oldValue: undefined
    } as any)

    expect(parent.contains(el)).toBe(false)
  })

  it('setupPermissionDirective 注册 v-permission 指令', () => {
    const app = {
      directive: vi.fn()
    }

    setupPermissionDirective(app as any)

    expect(app.directive).toHaveBeenCalledWith('permission', expect.any(Object))
  })
})
