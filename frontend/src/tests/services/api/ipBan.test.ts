import { describe, it, expect, vi, beforeEach } from 'vitest'

vi.mock('@/lib/services/request', () => ({ get: vi.fn(), post: vi.fn(), put: vi.fn() }))
beforeEach(() => {
  vi.clearAllMocks()
})

describe('ipBan API', () => {
  it('getIpBansApi', async () => {
    const { getIpBansApi } = await import('@/lib/services/api/ipBan')
    const { get } = await import('@/lib/services/request')
    vi.mocked(get).mockResolvedValue({ total: 1, page: 1, page_size: 20, list: [] })
    await getIpBansApi({ page: 1, page_size: 20 })
    expect(get).toHaveBeenCalledWith('/ip-ban/bans', { page: 1, page_size: 20 }, undefined)
  })

  it('getIpBansApi with filters', async () => {
    const { getIpBansApi } = await import('@/lib/services/api/ipBan')
    const { get } = await import('@/lib/services/request')
    vi.mocked(get).mockResolvedValue({ total: 1, page: 1, page_size: 20, list: [] })
    await getIpBansApi({ ban_type: 'manual', is_active: 'true', keyword: '192.168' })
    expect(get).toHaveBeenCalledWith(
      '/ip-ban/bans',
      { ban_type: 'manual', is_active: 'true', keyword: '192.168' },
      undefined
    )
  })

  it('banIpApi', async () => {
    const { banIpApi } = await import('@/lib/services/api/ipBan')
    const { post } = await import('@/lib/services/request')
    vi.mocked(post).mockResolvedValue({ id: 1, ip_or_cidr: '10.0.0.1', is_active: true })
    const payload = { ip_or_cidr: '10.0.0.1', reason: 'test', duration_minutes: 60 }
    await banIpApi(payload)
    expect(post).toHaveBeenCalledWith('/ip-ban/bans', payload, undefined)
  })

  it('batchUnbanApi', async () => {
    const { batchUnbanApi } = await import('@/lib/services/api/ipBan')
    const { post } = await import('@/lib/services/request')
    vi.mocked(post).mockResolvedValue({ count: 2 })
    await batchUnbanApi({ ban_ids: [1, 2] })
    expect(post).toHaveBeenCalledWith('/ip-ban/bans/batch-unban', { ban_ids: [1, 2] }, undefined)
  })

  it('unbanIpApi', async () => {
    const { unbanIpApi } = await import('@/lib/services/api/ipBan')
    const { post } = await import('@/lib/services/request')
    vi.mocked(post).mockResolvedValue({ id: 1, is_active: false })
    await unbanIpApi(1)
    expect(post).toHaveBeenCalledWith('/ip-ban/bans/1/unban', undefined, undefined)
  })

  it('getBanLogsApi', async () => {
    const { getBanLogsApi } = await import('@/lib/services/api/ipBan')
    const { get } = await import('@/lib/services/request')
    vi.mocked(get).mockResolvedValue({ total: 1, page: 1, page_size: 20, list: [] })
    await getBanLogsApi({ page: 1, action: 'ban' })
    expect(get).toHaveBeenCalledWith(
      '/ip-ban/logs',
      { page: 1, action: 'ban' },
      undefined
    )
  })

  it('getBanRulesApi', async () => {
    const { getBanRulesApi } = await import('@/lib/services/api/ipBan')
    const { get } = await import('@/lib/services/request')
    vi.mocked(get).mockResolvedValue([{ id: 'login_failure', name: '登录失败封禁', enabled: true, threshold: 10, window_seconds: 300, ban_duration_minutes: 30 }])
    await getBanRulesApi()
    expect(get).toHaveBeenCalledWith('/ip-ban/rules', undefined, undefined)
  })

  it('updateBanRuleApi', async () => {
    const { updateBanRuleApi } = await import('@/lib/services/api/ipBan')
    const { put } = await import('@/lib/services/request')
    vi.mocked(put).mockResolvedValue({ id: 'login_failure', threshold: 20 })
    await updateBanRuleApi('login_failure', { threshold: 20 })
    expect(put).toHaveBeenCalledWith('/ip-ban/rules/login_failure', { threshold: 20 }, undefined)
  })

  it('getIpBanStatsApi', async () => {
    const { getIpBanStatsApi } = await import('@/lib/services/api/ipBan')
    const { get } = await import('@/lib/services/request')
    vi.mocked(get).mockResolvedValue({ total_bans: 10, active_bans: 5, auto_bans: 3, manual_bans: 2, today_bans: 1 })
    await getIpBanStatsApi()
    expect(get).toHaveBeenCalledWith('/ip-ban/stats', undefined, undefined)
  })
})