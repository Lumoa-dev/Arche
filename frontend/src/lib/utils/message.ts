// 全局消息提示工具，不依赖于setup环境
import { createDiscreteApi } from 'naive-ui'

// 创建独立的消息实例
const { message, notification, dialog, loadingBar } = createDiscreteApi(
  ['message', 'notification', 'dialog', 'loadingBar'],
  {
    messageProviderProps: {
      duration: 3000,
      keepAliveOnHover: true
    }
  }
)

export const $message = message
export const $notification = notification
export const $dialog = dialog
export const $loadingBar = loadingBar
