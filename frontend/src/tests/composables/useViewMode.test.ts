import { describe, it, expect, vi, beforeEach } from 'vitest'

// ── Mock vue-router ──
const mockRoute = { query: {} as Record<string, string> }
const mockReplace = vi.fn()
const mockPush = vi.fn()

vi.mock('vue-router', () => ({
  useRoute: () => mockRoute,
  useRouter: () => ({
    replace: mockReplace,
    push: mockPush
  })
}))

// 在 useViewMode 导入之后重新导入
import { useViewMode } from '@/lib/composables/useViewMode'

describe('useViewMode', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
    mockRoute.query = {}
  })

  it('无 query 且无 localStorage 时返回默认模式', () => {
    const { viewMode } = useViewMode('test-key', 'detail')
    expect(viewMode.value).toBe('detail')
  })

  it('无 query 且无 localStorage 时返回 detail（默认默认值）', () => {
    const { viewMode } = useViewMode('test-key')
    expect(viewMode.value).toBe('detail')
  })

  it('localStorage 中的值生效', () => {
    localStorage.setItem('test-key', 'card')
    const { viewMode } = useViewMode('test-key', 'detail')
    expect(viewMode.value).toBe('card')
  })

  it('query 参数优先于 localStorage', () => {
    localStorage.setItem('test-key', 'card')
    mockRoute.query = { view: 'compact' }

    const { viewMode } = useViewMode('test-key', 'detail')
    expect(viewMode.value).toBe('compact')
  })

  it('query 参数为无效值时回退到 localStorage', () => {
    localStorage.setItem('test-key', 'card')
    mockRoute.query = { view: 'invalid' }

    const { viewMode } = useViewMode('test-key', 'detail')
    expect(viewMode.value).toBe('card')
  })

  it('设置 viewMode 时写入 localStorage 并更新路由 query', () => {
    const { viewMode } = useViewMode('test-key', 'detail')

    viewMode.value = 'compact'

    expect(localStorage.getItem('test-key')).toBe('compact')
    expect(mockReplace).toHaveBeenCalledWith({
      query: { view: 'compact' }
    })
  })

  it('设置 viewMode 保留已有 query 参数', () => {
    mockRoute.query = { search: 'hello' }
    const { viewMode } = useViewMode('test-key', 'detail')

    viewMode.value = 'card'

    expect(mockReplace).toHaveBeenCalledWith({
      query: { search: 'hello', view: 'card' }
    })
  })
})
