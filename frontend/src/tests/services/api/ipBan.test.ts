import { describe, it, expect, vi, beforeEach } from 'vitest'

vi.mock('@/lib/services/request', () => ({
  get: vi.fn(),
  post: vi.fn(),
  put: vi.fn()
}))

beforeEach(() => {
  vi.clearAllMocks()
})

describe('ipBan API', () => {
  it('getIpBansApi 发送正确 URL', async () => {
    const { getIpBansApi } = await import('@/lib/services/api/ipBan')
    const { get } = await import('@/lib/services/request')
    vi.mocked(get).mockResolvedValue({ list: [], total: 0 })

    await getIpBansApi({ page: 1, page_size: 20, ban_type: 'auto' })
    expect(get).toHaveBeenCalledWith(
      '/ip-ban/bans',
      { page: 1, page_size: 20, ban_type: 'auto' },
      undefined
    )
  })

  it('getIpBansApi 无参数时传 undefined', async () => {
    const { getIpBansApi } = await import('@/lib/services/api/ipBan')
    const { get } = await import('@/lib/services/request')
    vi.mocked(get).mockResolvedValue({ list: [], total: 0 })

    await getIpBansApi(undefined)
    expect(get).toHaveBeenCalledWith('/ip-ban/bans', undefined, undefined)
  })

  it('banIpApi 发送 POST 请求', async () => {
    const { banIpApi } = await import('@/lib/services/api/ipBan')
    const { post } = await import('@/lib/services/request')
    vi.mocked(post).mockResolvedValue({ id: 1, ip_or_cidr: '192.168.1.1' })

    const payload = { ip_or_cidr: '192.168.1.1', reason: '恶意攻击', duration_minutes: 60 }
    await banIpApi(payload)
    expect(post).toHaveBeenCalledWith('/ip-ban/bans', payload, undefined)
  })

  it('banIpApi 无 duration 时传 null', async () => {
    const { banIpApi } = await import('@/lib/services/api/ipBan')
    const { post } = await import('@/lib/services/request')
    vi.mocked(post).mockResolvedValue({ id: 1 })

    await banIpApi({ ip_or_cidr: '10.0.0.1', reason: 'test', duration_minutes: null })
    expect(post).toHaveBeenCalledWith(
      '/ip-ban/bans',
      { ip_or_cidr: '10.0.0.1', reason: 'test', duration_minutes: null },
      undefined
    )
  })

  it('unbanIpApi 发送 POST 到正确路径', async () => {
    const { unbanIpApi } = await import('@/lib/services/api/ipBan')
    const { post } = await import('@/lib/services/request')
    vi.mocked(post).mockResolvedValue({ id: 1 })

    await unbanIpApi(42)
    expect(post).toHaveBeenCalledWith('/ip-ban/bans/42/unban', undefined, undefined)
  })

  it('batchUnbanApi 发送 POST 请求', async () => {
    const { batchUnbanApi } = await import('@/lib/services/api/ipBan')
    const { post } = await import('@/lib/services/request')
    vi.mocked(post).mockResolvedValue({ count: 2 })

    await batchUnbanApi({ ban_ids: [1, 2, 3] })
    expect(post).toHaveBeenCalledWith(
      '/ip-ban/bans/batch-unban',
      { ban_ids: [1, 2, 3] },
      undefined
    )
  })

  it('getBanLogsApi 发送正确 URL', async () => {
    const { getBanLogsApi } = await import('@/lib/services/api/ipBan')
    const { get } = await import('@/lib/services/request')
    vi.mocked(get).mockResolvedValue({ list: [], total: 0 })

    await getBanLogsApi({ page: 1, action: 'ban' })
    expect(get).toHaveBeenCalledWith(
      '/ip-ban/logs',
      { page: 1, action: 'ban' },
      undefined
    )
  })

  it('getBanRulesApi 发送正确 URL', async () => {
    const { getBanRulesApi } = await import('@/lib/services/api/ipBan')
    const { get } = await import('@/lib/services/request')
    vi.mocked(get).mockResolvedValue([{ id: 'login_failure', name: '登录失败封禁' }])

    await getBanRulesApi()
    expect(get).toHaveBeenCalledWith('/ip-ban/rules', undefined, undefined)
  })

  it('updateBanRuleApi 发送 PUT 请求', async () => {
    const { updateBanRuleApi } = await import('@/lib/services/api/ipBan')
    const { put } = await import('@/lib/services/request')
    vi.mocked(put).mockResolvedValue({ id: 'login_failure', enabled: false })

    await updateBanRuleApi('login_failure', { enabled: false, threshold: 20 })
    expect(put).toHaveBeenCalledWith(
      '/ip-ban/rules/login_failure',
      { enabled: false, threshold: 20 },
      undefined
    )
  })

  it('getIpBanStatsApi 发送正确 URL', async () => {
    const { getIpBanStatsApi } = await import('@/lib/services/api/ipBan')
    const { get } = await import('@/lib/services/request')
    vi.mocked(get).mockResolvedValue({ total_bans: 10, active_bans: 5 })

    await getIpBanStatsApi()
    expect(get).toHaveBeenCalledWith('/ip-ban/stats', undefined, undefined)
  })
})