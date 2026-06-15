import { describe, it, expect, vi, beforeEach, beforeAll, type Mock } from 'vitest'
import type { AxiosResponse } from 'axios'

// ══════════════════════════════════════════════
// 1. Mock 依赖 — 全部用 vi.hoisted 包裹，确保工厂可访问
// ══════════════════════════════════════════════

const mocks = vi.hoisted(() => {
  // 可变状态
  const capturedReqHandler: { current: any } = { current: null }
  const capturedResHandler: { current: any } = { current: null }
  const capturedErrHandler: { current: any } = { current: null }
  const serviceInstance: { current: any } = { current: null }

  class MockAxiosError extends Error {
    code?: string
    config?: any
    request?: any
    response?: any
    name = 'AxiosError'
    constructor(
      msg: string,
      opts?: { code?: string; config?: any; request?: any; response?: any }
    ) {
      super(msg)
      if (opts) Object.assign(this, opts)
    }
  }

  class MockCanceledError extends Error {
    name = 'CanceledError'
  }

  function createMockAxiosInstance() {
    return {
      interceptors: {
        request: { use: vi.fn(), eject: vi.fn() },
        response: { use: vi.fn(), eject: vi.fn() }
      },
      request: vi.fn(),
      post: vi.fn(),
      get: vi.fn(),
      put: vi.fn(),
      delete: vi.fn()
    }
  }

  // localStorage mock（也放进 hoisted 避免 window 操作时机问题）
  const store: Record<string, string> = {}
  const localStore = {
    getItem: (key: string) => store[key] ?? null,
    setItem: (key: string, value: string) => {
      store[key] = value
    },
    removeItem: (key: string) => {
      delete store[key]
    },
    clear: () => {
      Object.keys(store).forEach((k) => delete store[k])
    },
    get length() {
      return Object.keys(store).length
    },
    key: (i: number) => Object.keys(store)[i] ?? null
  }

  return {
    capturedReqHandler,
    capturedResHandler,
    capturedErrHandler,
    serviceInstance,
    MockAxiosError,
    MockCanceledError,
    createMockAxiosInstance,
    store,
    localStore
  }
})

// 注册 localStorage 到 window
Object.defineProperty(window, 'localStorage', {
  value: mocks.localStore,
  configurable: true,
  writable: true
})

// ── axios mock ──
vi.mock('axios', () => {
  function createInstance() {
    const instance = mocks.createMockAxiosInstance()

    // 覆盖 interceptors.use 来捕获 handler
    instance.interceptors.request.use = vi.fn((h: any) => {
      mocks.capturedReqHandler.current = h
      return 0
    })
    instance.interceptors.response.use = vi.fn((h: any, eh: any) => {
      mocks.capturedResHandler.current = h
      mocks.capturedErrHandler.current = eh
      return 0
    })

    // 第一个 create 调用保存为 serviceInstance
    if (!mocks.serviceInstance.current) {
      mocks.serviceInstance.current = instance
    }

    return instance
  }

  return {
    default: {
      create: vi.fn(() => createInstance()),
      isCancel: (e: any) => e instanceof mocks.MockCanceledError
    },
    AxiosError: mocks.MockAxiosError,
    CanceledError: mocks.MockCanceledError
  }
})

vi.mock('@/lib/utils/message', () => ({
  $message: { error: vi.fn() }
}))

// ══════════════════════════════════════════════
// 2. 测试
// ══════════════════════════════════════════════
describe('request.ts', () => {
  let get: typeof import('@/lib/services/request').get
  let post: typeof import('@/lib/services/request').post
  let put: typeof import('@/lib/services/request').put
  let del: typeof import('@/lib/services/request').del
  let upload: typeof import('@/lib/services/request').upload
  let cancelAllPendingRequests: typeof import('@/lib/services/request').cancelAllPendingRequests
  let $message: { error: Mock }
  let AUTH_UNAUTHORIZED_EVENT: string

  beforeAll(async () => {
    const mod = await import('@/lib/services/request')
    get = mod.get
    post = mod.post
    put = mod.put
    del = mod.del
    upload = mod.upload
    cancelAllPendingRequests = mod.cancelAllPendingRequests
    $message = (await import('@/lib/utils/message')).$message as unknown as { error: Mock }
    AUTH_UNAUTHORIZED_EVENT = (await import('@/lib/constants/auth')).AUTH_UNAUTHORIZED_EVENT
  })

  beforeEach(() => {
    vi.clearAllMocks()
    Object.keys(mocks.store).forEach((k) => delete mocks.store[k])
  })

  // ── 请求拦截器 ──
  describe('请求拦截器', () => {
    function makeConfig(overrides?: Record<string, any>) {
      return { url: '/api/test', method: 'get', headers: {}, ...overrides } as any
    }

    it('有 token 时添加 Authorization header', () => {
      mocks.store.token = 'my-token'
      const result = mocks.capturedReqHandler.current(makeConfig())
      expect(result.headers.Authorization).toBe('Bearer my-token')
    })

    it('无 token 时跳过 Authorization', () => {
      const result = mocks.capturedReqHandler.current(makeConfig())
      expect(result.headers?.Authorization).toBeUndefined()
    })

    it('POST 请求默认启用请求去重', () => {
      const result = mocks.capturedReqHandler.current(makeConfig({ method: 'post', data: '{}' }))
      expect(result.dedupeKey).toBeDefined()
      expect(result.signal).toBeDefined()
    })

    it('GET 请求默认不启用去重', () => {
      const result = mocks.capturedReqHandler.current(makeConfig())
      expect(result.dedupeKey).toBeUndefined()
    })

    it('dedupe: false 强制关闭去重', () => {
      const result = mocks.capturedReqHandler.current(
        makeConfig({ method: 'post', data: '{}', requestOptions: { dedupe: false } })
      )
      expect(result.dedupeKey).toBeUndefined()
    })

    it('相同 key 的重复请求会取消前一个', () => {
      const resultA = mocks.capturedReqHandler.current(makeConfig({ method: 'post', data: '{}' }))
      const signalA = resultA.signal
      mocks.capturedReqHandler.current(makeConfig({ method: 'post', data: '{}' }))
      expect(signalA.aborted).toBe(true)
    })

    it('自定义 dedupeKey 生效', () => {
      const result = mocks.capturedReqHandler.current(
        makeConfig({ method: 'get', requestOptions: { dedupe: true, dedupeKey: 'custom-key' } })
      )
      expect(result.dedupeKey).toBe('custom-key')
    })
  })

  // ── 响应成功拦截器 ──
  describe('响应成功拦截器', () => {
    function makeResponse(data: any, config?: any): AxiosResponse {
      return {
        data,
        status: 200,
        statusText: 'OK',
        headers: {},
        config: config ?? { requestOptions: {} }
      } as AxiosResponse
    }

    it('code=200 时返回 data', async () => {
      const res = makeResponse({ code: 200, data: { id: 1 }, message: 'ok' })
      const result = await mocks.capturedResHandler.current(res)
      expect(result).toEqual({ id: 1 })
    })

    it('code="ok" 时返回 data', async () => {
      const res = makeResponse({ code: 'ok', data: { id: 1 }, message: 'ok' })
      const result = await mocks.capturedResHandler.current(res)
      expect(result).toEqual({ id: 1 })
    })

    it('success=true 时返回 data', async () => {
      const res = makeResponse({ success: true, data: { id: 1 }, message: 'ok' })
      const result = await mocks.capturedResHandler.current(res)
      expect(result).toEqual({ id: 1 })
    })

    it('非成功 code 时 reject + 弹错误提示', async () => {
      const res = makeResponse(
        { code: 400, message: '参数错误', data: null },
        { requestOptions: {} }
      )
      await expect(mocks.capturedResHandler.current(res)).rejects.toThrow('参数错误')
      expect($message.error).toHaveBeenCalledWith('参数错误')
    })

    it('silent 模式下不弹错误提示', async () => {
      const res = makeResponse(
        { code: 400, message: '参数错误', data: null },
        { requestOptions: { silent: true } }
      )
      await expect(mocks.capturedResHandler.current(res)).rejects.toThrow()
      expect($message.error).not.toHaveBeenCalled()
    })

    it('401 时清除登录态 + 派发事件', async () => {
      const dispatchSpy = vi.spyOn(window, 'dispatchEvent')
      mocks.store.token = 'xxx'
      mocks.store.refresh_token = 'xxx'
      mocks.store.userInfo = '{}'
      const res = makeResponse({ code: 401, message: '未登录', data: null }, { requestOptions: {} })
      await expect(mocks.capturedResHandler.current(res)).rejects.toThrow()
      expect(mocks.store.token).toBeUndefined()
      expect(mocks.store.refresh_token).toBeUndefined()
      expect(mocks.store.userInfo).toBeUndefined()
      expect(dispatchSpy).toHaveBeenCalledWith(
        expect.objectContaining({ type: AUTH_UNAUTHORIZED_EVENT })
      )
    })

    it('403 时弹权限不足提示', async () => {
      const res = makeResponse(
        { code: 403, message: '权限不足', data: null },
        { requestOptions: {} }
      )
      await expect(mocks.capturedResHandler.current(res)).rejects.toThrow()
      expect($message.error).toHaveBeenCalledWith('权限不足，无法访问')
    })

    it('items → list 转换（分页数据归一化）', async () => {
      const res = makeResponse({ code: 200, data: { items: [1, 2, 3], total: 3 }, message: 'ok' })
      const result = await mocks.capturedResHandler.current(res)
      expect(result).toEqual({ items: [1, 2, 3], total: 3, list: [1, 2, 3] })
    })

    it('字符串 data 直接返回', async () => {
      const res = makeResponse({ code: 200, data: 'plain', message: 'ok' })
      const result = await mocks.capturedResHandler.current(res)
      expect(result).toBe('plain')
    })
  })

  // ── 响应错误拦截器 ──
  describe('响应错误拦截器', () => {
    it('CanceledError 直接 reject 不弹提示', async () => {
      const err = new mocks.MockCanceledError('cancelled')
      await expect(mocks.capturedErrHandler.current(err)).rejects.toThrow('cancelled')
      expect($message.error).not.toHaveBeenCalled()
    })

    it('401 无 refresh_token 时清空登录态', async () => {
      mocks.store.token = 'old'
      const err = new mocks.MockAxiosError('Unauthorized', {
        config: { url: '/api/data', requestOptions: {} },
        response: { status: 401, data: {} }
      })
      await expect(mocks.capturedErrHandler.current(err)).rejects.toThrow()
      expect(mocks.store.token).toBeUndefined()
    })

    it('401 refresh 请求本身失败时直接处理', async () => {
      mocks.store.refresh_token = 'xxx'
      const err = new mocks.MockAxiosError('Unauthorized', {
        config: { url: '/api/auth/refresh', requestOptions: {} },
        response: { status: 401, data: {} }
      })
      await expect(mocks.capturedErrHandler.current(err)).rejects.toThrow()
    })

    it('400 时提示参数错误', async () => {
      const err = new mocks.MockAxiosError('Bad Request', {
        config: { url: '/api/data', requestOptions: {} },
        response: { status: 400, data: {} }
      })
      await expect(mocks.capturedErrHandler.current(err)).rejects.toThrow()
      expect($message.error).toHaveBeenCalledWith('请求参数错误')
    })

    it('404 时提示资源不存在', async () => {
      const err = new mocks.MockAxiosError('Not Found', {
        config: { url: '/api/data', requestOptions: {} },
        response: { status: 404, data: {} }
      })
      await expect(mocks.capturedErrHandler.current(err)).rejects.toThrow()
      expect($message.error).toHaveBeenCalledWith('请求的资源不存在')
    })

    it('500 时提示服务器内部错误', async () => {
      const err = new mocks.MockAxiosError('Server Error', {
        config: { url: '/api/data', requestOptions: {} },
        response: { status: 500, data: {} }
      })
      await expect(mocks.capturedErrHandler.current(err)).rejects.toThrow()
      expect($message.error).toHaveBeenCalledWith('服务器内部错误')
    })

    it('silent 模式下不弹错误提示', async () => {
      const err = new mocks.MockAxiosError('Not Found', {
        config: { url: '/api/data', requestOptions: { silent: true } },
        response: { status: 404, data: {} }
      })
      await expect(mocks.capturedErrHandler.current(err)).rejects.toThrow()
      expect($message.error).not.toHaveBeenCalled()
    })

    it('网络异常时提示网络错误', async () => {
      const err = new mocks.MockAxiosError('Network Error', {
        config: { url: '/api/data', requestOptions: {} },
        code: 'ERR_NETWORK'
      })
      await expect(mocks.capturedErrHandler.current(err)).rejects.toThrow()
      expect($message.error).toHaveBeenCalled()
    })
  })

  // ── 导出方法 ──
  describe('导出请求方法', () => {
    it('get 发送 GET 请求', async () => {
      mocks.serviceInstance.current.request.mockResolvedValue('ok')
      await get('/api/test', { page: 1 })
      expect(mocks.serviceInstance.current.request).toHaveBeenCalledWith(
        expect.objectContaining({ method: 'get', url: '/api/test', params: { page: 1 } })
      )
    })

    it('post 发送 POST 请求', async () => {
      mocks.serviceInstance.current.request.mockResolvedValue('ok')
      await post('/api/test', { name: 'test' })
      expect(mocks.serviceInstance.current.request).toHaveBeenCalledWith(
        expect.objectContaining({ method: 'post', url: '/api/test', data: { name: 'test' } })
      )
    })

    it('put 发送 PUT 请求', async () => {
      mocks.serviceInstance.current.request.mockResolvedValue('ok')
      await put('/api/test/1', { name: 'updated' })
      expect(mocks.serviceInstance.current.request).toHaveBeenCalledWith(
        expect.objectContaining({ method: 'put', url: '/api/test/1' })
      )
    })

    it('del 发送 DELETE 请求', async () => {
      mocks.serviceInstance.current.request.mockResolvedValue('ok')
      await del('/api/test/1')
      expect(mocks.serviceInstance.current.request).toHaveBeenCalledWith(
        expect.objectContaining({ method: 'delete', url: '/api/test/1' })
      )
    })

    it('upload 发送 multipart/form-data 请求', async () => {
      mocks.serviceInstance.current.request.mockResolvedValue('ok')
      const file = new File(['content'], 'test.txt', { type: 'text/plain' })
      await upload('/api/upload', file)
      expect(mocks.serviceInstance.current.request).toHaveBeenCalledWith(
        expect.objectContaining({
          method: 'post',
          url: '/api/upload',
          headers: { 'Content-Type': 'multipart/form-data' }
        })
      )
    })

    it('cancelAllPendingRequests 不抛异常', () => {
      mocks.capturedReqHandler.current({
        url: '/api/test',
        method: 'post',
        data: '{}',
        headers: {}
      })
      cancelAllPendingRequests()
    })
  })
})
