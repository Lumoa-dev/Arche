import type { App } from 'vue'
import { setupPermissionDirective } from './permission'

// 注册所有自定义指令
export function setupDirectives(app: App) {
  setupPermissionDirective(app)
  // 后续新增的指令在这里注册
  // setupXXXDirective(app)
}
