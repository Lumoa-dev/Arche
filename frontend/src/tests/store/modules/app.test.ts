import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useAppStore } from '@/lib/store/modules/app'

// 模拟 window.matchMedia
function createMatchMediaMock(matches: boolean) {
  return vi.fn().mockImplementation((query: string) => ({
    matches,
    media: query,
    onchange: null,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    addListener: vi.fn(),
    removeListener: vi.fn(),
    dispatchEvent: vi.fn()
  }))
}

describe('useAppStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    // 默认模拟浅色主题
    window.matchMedia = createMatchMediaMock(false)
  })

  describe('初始状态', () => {
    it('theme 默认跟随系统（模拟 light）', () => {
      const store = useAppStore()
      expect(store.theme).toBe('light')
    })

    it('layout 默认为 default', () => {
      const store = useAppStore()
      expect(store.layout).toBe('default')
    })

    it('sidebarCollapsed 默认为 false', () => {
      const store = useAppStore()
      expect(store.sidebarCollapsed).toBe(false)
    })

    it('breadcrumbVisible / tabsVisible / footerVisible 默认均为 true', () => {
      const store = useAppStore()
      expect(store.breadcrumbVisible).toBe(true)
      expect(store.tabsVisible).toBe(true)
      expect(store.footerVisible).toBe(true)
    })

    it('language 默认为 zh-CN', () => {
      const store = useAppStore()
      expect(store.language).toBe('zh-CN')
    })

    it('transitionName 默认为 fade-transform', () => {
      const store = useAppStore()
      expect(store.transitionName).toBe('fade-transform')
    })

    it('isMobile 默认为 false', () => {
      const store = useAppStore()
      expect(store.isMobile).toBe(false)
    })
  })

  describe('toggleTheme', () => {
    it('从 light 切换到 dark', () => {
      const store = useAppStore()
      store.toggleTheme()
      expect(store.theme).toBe('dark')
      expect(document.documentElement.classList.contains('dark')).toBe(true)
    })

    it('从 dark 切换到 light', () => {
      window.matchMedia = createMatchMediaMock(true) // 模拟深色系统主题
      const store = useAppStore()
      store.toggleTheme()
      expect(store.theme).toBe('light')
      expect(document.documentElement.classList.contains('dark')).toBe(false)
    })
  })

  describe('setTheme', () => {
    it('设置为 dark', () => {
      const store = useAppStore()
      store.setTheme('dark')
      expect(store.theme).toBe('dark')
      expect(document.documentElement.classList.contains('dark')).toBe(true)
    })

    it('设置为 light', () => {
      const store = useAppStore()
      store.setTheme('light')
      expect(store.theme).toBe('light')
      expect(document.documentElement.classList.contains('dark')).toBe(false)
    })
  })

  describe('initTheme', () => {
    it('应用当前 theme 的 class', () => {
      const store = useAppStore()
      store.setTheme('dark')
      // 手动移除 class 模拟初始化场景
      document.documentElement.classList.remove('dark')
      store.initTheme()
      expect(document.documentElement.classList.contains('dark')).toBe(true)
    })
  })

  describe('toggleSidebar', () => {
    it('切换 sidebarCollapsed 状态', () => {
      const store = useAppStore()
      expect(store.sidebarCollapsed).toBe(false)
      store.toggleSidebar()
      expect(store.sidebarCollapsed).toBe(true)
      store.toggleSidebar()
      expect(store.sidebarCollapsed).toBe(false)
    })
  })

  describe('setSidebarCollapsed', () => {
    it('设置折叠为 true', () => {
      const store = useAppStore()
      store.setSidebarCollapsed(true)
      expect(store.sidebarCollapsed).toBe(true)
    })

    it('设置折叠为 false', () => {
      const store = useAppStore()
      store.setSidebarCollapsed(false)
      expect(store.sidebarCollapsed).toBe(false)
    })
  })

  describe('setLayout', () => {
    it('设置为 simple', () => {
      const store = useAppStore()
      store.setLayout('simple')
      expect(store.layout).toBe('simple')
    })

    it('设置为 default', () => {
      const store = useAppStore()
      store.setLayout('simple')
      store.setLayout('default')
      expect(store.layout).toBe('default')
    })
  })

  describe('setTransitionName', () => {
    it('设置动画名称', () => {
      const store = useAppStore()
      store.setTransitionName('slide')
      expect(store.transitionName).toBe('slide')
    })
  })

  describe('setMobile', () => {
    it('设置移动端模式为 true', () => {
      const store = useAppStore()
      store.setMobile(true)
      expect(store.isMobile).toBe(true)
    })

    it('设置移动端模式为 false', () => {
      const store = useAppStore()
      store.setMobile(false)
      expect(store.isMobile).toBe(false)
    })
  })

  describe('resetState', () => {
    it('重置所有状态为默认值', () => {
      const store = useAppStore()
      // 先修改各种状态
      store.setTheme('dark')
      store.setLayout('simple')
      store.setSidebarCollapsed(true)
      store.setTransitionName('slide')
      store.setMobile(true)

      store.resetState()

      expect(store.theme).toBe('light')
      expect(store.layout).toBe('default')
      expect(store.sidebarCollapsed).toBe(false)
      expect(store.breadcrumbVisible).toBe(true)
      expect(store.tabsVisible).toBe(true)
      expect(store.footerVisible).toBe(true)
      expect(store.language).toBe('zh-CN')
      expect(store.transitionName).toBe('fade-transform')
      expect(store.isMobile).toBe(false)
    })

    it('重置后应用主题 class', () => {
      const store = useAppStore()
      store.setTheme('dark')
      store.resetState()
      expect(document.documentElement.classList.contains('dark')).toBe(false)
    })
  })
})
