import { createApp } from 'vue'
import App from './App.vue'
import router from './lib/router'
import pinia from './store'
import { setupDirectives } from './directives'
import './lib/router/guard'
import './styles/theme.css'
import { useAppStore } from '@/lib/store/modules/app'

const app = createApp(App)

app.use(pinia)
app.use(router)

const appStore = useAppStore()
appStore.initTheme()

const syncViewportState = () => {
  appStore.setMobile(window.innerWidth < 992)
  if (appStore.isMobile) {
    appStore.setSidebarCollapsed(true)
  }
}

syncViewportState()
window.addEventListener('resize', syncViewportState)

// 注册自定义指令
setupDirectives(app)

app.mount('#app')
