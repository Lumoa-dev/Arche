/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** 应用名称 */
  readonly VITE_APP_NAME: string
  /** 应用版本 */
  readonly VITE_APP_VERSION: string
  /** 环境类型 */
  readonly VITE_NODE_ENV: 'development' | 'test' | 'production'
  /** API基础地址 */
  readonly VITE_API_BASE_URL: string
  /** 是否开启调试模式 */
  readonly VITE_ENABLE_DEBUG: boolean
  /** 是否使用演示登录 */
  readonly VITE_USE_MOCK_LOGIN?: 'true' | 'false'
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
