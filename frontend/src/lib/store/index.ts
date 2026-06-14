import { createPinia } from 'pinia'
import piniaPluginPersistedstate from 'pinia-plugin-persistedstate'
import { useAppStore } from './modules/app'
import { usePermissionStore } from './modules/permission'
import { useUserStore } from './modules/user'

const pinia = createPinia()
// 注册持久化插件
pinia.use(piniaPluginPersistedstate)

export const resetAllStores = () => {
  const appStore = useAppStore(pinia)
  const userStore = useUserStore(pinia)
  const permissionStore = usePermissionStore(pinia)

  permissionStore.resetState()
  userStore.resetState()
  appStore.resetState()
}

// 导出所有store
export * from './modules/user'
export * from './modules/app'
export * from './modules/permission'

export default pinia
