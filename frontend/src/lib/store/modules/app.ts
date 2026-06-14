import { defineStore } from 'pinia'
import { ref } from 'vue'

export type Theme = 'light' | 'dark'

export type LayoutType = 'default' | 'simple'

export const useAppStore = defineStore(
  'app',
  () => {
    const getSystemTheme = (): Theme =>
      window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'

    const applyThemeClass = (value: Theme) => {
      document.documentElement.classList.toggle('dark', value === 'dark')
    }

    // 主题
    const theme = ref<Theme>(getSystemTheme())
    // 布局方式
    const layout = ref<LayoutType>('default')
    // 侧边栏是否折叠
    const sidebarCollapsed = ref(false)
    // 是否显示面包屑
    const breadcrumbVisible = ref(true)
    // 是否显示标签栏
    const tabsVisible = ref(true)
    // 是否显示页脚
    const footerVisible = ref(true)
    // 语言
    const language = ref('zh-CN')
    // 页面切换动画
    const transitionName = ref('fade-transform')
    // 移动端模式
    const isMobile = ref(false)

    // 切换主题
    const toggleTheme = () => {
      theme.value = theme.value === 'light' ? 'dark' : 'light'
      applyThemeClass(theme.value)
    }

    const setTheme = (value: Theme) => {
      theme.value = value
      applyThemeClass(theme.value)
    }

    const initTheme = () => {
      applyThemeClass(theme.value)
    }

    // 切换侧边栏折叠状态
    const toggleSidebar = () => {
      sidebarCollapsed.value = !sidebarCollapsed.value
    }

    // 设置折叠状态
    const setSidebarCollapsed = (collapsed: boolean) => {
      sidebarCollapsed.value = collapsed
    }

    // 切换布局
    const setLayout = (newLayout: LayoutType) => {
      layout.value = newLayout
    }

    const setTransitionName = (name: string) => {
      transitionName.value = name
    }

    const setMobile = (value: boolean) => {
      isMobile.value = value
    }

    const resetState = () => {
      theme.value = getSystemTheme()
      layout.value = 'default'
      sidebarCollapsed.value = false
      breadcrumbVisible.value = true
      tabsVisible.value = true
      footerVisible.value = true
      language.value = 'zh-CN'
      transitionName.value = 'fade-transform'
      isMobile.value = false
      applyThemeClass(theme.value)
    }

    return {
      theme,
      layout,
      sidebarCollapsed,
      breadcrumbVisible,
      tabsVisible,
      footerVisible,
      language,
      transitionName,
      isMobile,
      toggleTheme,
      setTheme,
      initTheme,
      toggleSidebar,
      setSidebarCollapsed,
      setLayout,
      setTransitionName,
      setMobile,
      resetState
    }
  },
  {
    persist: {
      pick: ['theme', 'layout', 'sidebarCollapsed', 'language', 'transitionName']
    }
  }
)
