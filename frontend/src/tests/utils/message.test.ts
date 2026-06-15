import { describe, it, expect, vi, beforeEach } from 'vitest'

// ── mock naive-ui ──
// 需要在 import 被测试模块之前，通过 vi.mock 的 hoisting 机制

const mockDiscreteApi = {
  message: {
    info: vi.fn(),
    success: vi.fn(),
    warning: vi.fn(),
    error: vi.fn()
  },
  notification: {
    info: vi.fn(),
    success: vi.fn(),
    warning: vi.fn(),
    error: vi.fn()
  },
  dialog: {
    info: vi.fn(),
    success: vi.fn(),
    warning: vi.fn(),
    error: vi.fn()
  },
  loadingBar: {
    start: vi.fn(),
    finish: vi.fn(),
    error: vi.fn()
  }
}

const mockCreateDiscreteApi = vi.fn(() => mockDiscreteApi)

vi.mock('naive-ui', () => ({
  createDiscreteApi: mockCreateDiscreteApi
}))

describe('message 工具模块', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('$message', () => {
    it('应该导出 message 实例', async () => {
      const { $message } = await import('@/lib/utils/message')
      expect($message).toBe(mockDiscreteApi.message)
    })
  })

  describe('$notification', () => {
    it('应该导出 notification 实例', async () => {
      const { $notification } = await import('@/lib/utils/message')
      expect($notification).toBe(mockDiscreteApi.notification)
    })
  })

  describe('$dialog', () => {
    it('应该导出 dialog 实例', async () => {
      const { $dialog } = await import('@/lib/utils/message')
      expect($dialog).toBe(mockDiscreteApi.dialog)
    })
  })

  describe('$loadingBar', () => {
    it('应该导出 loadingBar 实例', async () => {
      const { $loadingBar } = await import('@/lib/utils/message')
      expect($loadingBar).toBe(mockDiscreteApi.loadingBar)
    })
  })
})
