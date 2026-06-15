import { describe, it, expect, vi } from 'vitest'
import type { Component } from 'vue'
import type { RouteRecordRaw } from 'vue-router'

vi.mock('@/icons', async (importOriginal) => {
  const mod = (await importOriginal()) as Record<string, Component>
  return {
    ...mod,
    HomeOutline: { name: 'HomeOutline' } as Component,
    SettingsOutline: { name: 'SettingsOutline' } as Component
  }
})

describe('buildLayoutMenus', () => {
  it('按 layout 过滤并返回菜单项', async () => {
    const { buildLayoutMenus } = await import('@/lib/router/menu')

    const routes: RouteRecordRaw[] = [
      {
        path: '/user',
        meta: { title: '用户中心', layout: 'user' },
        component: {} as any
      },
      {
        path: '/admin',
        meta: { title: '管理后台', layout: 'admin' },
        component: {} as any
      },
      {
        path: '/public',
        meta: { title: '公开页', layout: 'guest' },
        component: {} as any
      }
    ]

    const userMenus = buildLayoutMenus(routes, 'user')
    expect(userMenus).toHaveLength(1)
    expect(userMenus[0]).toMatchObject({ title: '用户中心', path: '/user' })
  })

  it('menu: false 的路由不加入菜单', async () => {
    const { buildLayoutMenus } = await import('@/lib/router/menu')

    const routes: RouteRecordRaw[] = [
      {
        path: '/hidden',
        meta: { title: '隐藏菜单', layout: 'user', menu: false },
        component: {} as any
      },
      {
        path: '/visible',
        meta: { title: '可见菜单', layout: 'user' },
        component: {} as any
      }
    ]

    const menus = buildLayoutMenus(routes, 'user')
    expect(menus).toHaveLength(1)
    expect(menus[0]!.title).toBe('可见菜单')
  })

  it('没有 title 的路由不加入菜单', async () => {
    const { buildLayoutMenus } = await import('@/lib/router/menu')

    const routes: RouteRecordRaw[] = [
      {
        path: '/no-title',
        meta: { layout: 'user' },
        component: {} as any
      }
    ]

    const menus = buildLayoutMenus(routes, 'user')
    expect(menus).toHaveLength(0)
  })

  it('没有 meta 的路由不加入菜单', async () => {
    const { buildLayoutMenus } = await import('@/lib/router/menu')

    const routes: RouteRecordRaw[] = [
      {
        path: '/no-meta',
        component: {} as any
      }
    ]

    const menus = buildLayoutMenus(routes, 'user')
    expect(menus).toHaveLength(0)
  })

  it('解析 icon 并附加到菜单项', async () => {
    const { buildLayoutMenus } = await import('@/lib/router/menu')

    const routes: RouteRecordRaw[] = [
      {
        path: '/home',
        meta: { title: '首页', layout: 'user', icon: 'HomeOutline' },
        component: {} as any
      }
    ]

    const menus = buildLayoutMenus(routes, 'user')
    expect(menus[0]!.icon).toBeDefined()
    expect(menus[0]!.icon).toMatchObject({ name: 'HomeOutline' })
  })

  it('无 icon 配置时 icon 为 undefined', async () => {
    const { buildLayoutMenus } = await import('@/lib/router/menu')

    const routes: RouteRecordRaw[] = [
      {
        path: '/home',
        meta: { title: '首页', layout: 'user' },
        component: {} as any
      }
    ]

    const menus = buildLayoutMenus(routes, 'user')
    expect(menus[0]!.icon).toBeUndefined()
  })

  it('递归处理子路由', async () => {
    const { buildLayoutMenus } = await import('@/lib/router/menu')

    const routes: RouteRecordRaw[] = [
      {
        path: '/parent',
        meta: { title: '父级', layout: 'user' },
        component: {} as any,
        children: [
          {
            path: 'child',
            meta: { title: '子级', layout: 'user' },
            component: {} as any
          }
        ]
      }
    ]

    const menus = buildLayoutMenus(routes, 'user')
    expect(menus).toHaveLength(2)
    expect(menus[0]!.title).toBe('父级')
    expect(menus[0]!.path).toBe('/parent')
    expect(menus[1]!.title).toBe('子级')
    expect(menus[1]!.path).toBe('/parent/child')
  })

  it('子路由以 / 开头时直接拼接', async () => {
    const { buildLayoutMenus } = await import('@/lib/router/menu')

    const routes: RouteRecordRaw[] = [
      {
        path: '/parent',
        meta: { title: '父级', layout: 'user' },
        component: {} as any,
        children: [
          {
            path: '/absolute-child',
            meta: { title: '绝对路径子级', layout: 'user' },
            component: {} as any
          }
        ]
      }
    ]

    const menus = buildLayoutMenus(routes, 'user')
    expect(menus[1]!.path).toBe('/absolute-child')
  })

  it('子路由 path 为空时继承父路径', async () => {
    const { buildLayoutMenus } = await import('@/lib/router/menu')

    const routes: RouteRecordRaw[] = [
      {
        path: '/parent',
        meta: { title: '父级', layout: 'user' },
        component: {} as any,
        children: [
          {
            path: '',
            meta: { title: '空路径子级', layout: 'user' },
            component: {} as any
          }
        ]
      }
    ]

    const menus = buildLayoutMenus(routes, 'user')
    expect(menus[1]!.path).toBe('/parent')
  })

  it('父路径以 / 结尾时正常拼接', async () => {
    const { buildLayoutMenus } = await import('@/lib/router/menu')

    const routes: RouteRecordRaw[] = [
      {
        path: '/parent/',
        meta: { title: '父级', layout: 'user' },
        component: {} as any,
        children: [
          {
            path: 'child',
            meta: { title: '子级', layout: 'user' },
            component: {} as any
          }
        ]
      }
    ]

    const menus = buildLayoutMenus(routes, 'user')
    expect(menus[1]!.path).toBe('/parent/child')
  })
})
