import { describe, it, expect, vi, beforeEach } from 'vitest'

vi.mock('@/lib/services/request', () => ({
  get: vi.fn(),
  post: vi.fn(),
  put: vi.fn(),
  del: vi.fn()
}))

beforeEach(() => {
  vi.clearAllMocks()
})

describe('ipBan API', () => {
  it('getIpBansApi 传递查询参数', async () => {
    const { getIpBansApi } = await import('@/lib/services/api/ipBan')
    const { get } = await import('@/lib/services/request')
    vi.mocked(get).mockResolvedValue({ list: [], total: 0 })
    await getIpBansApi({ page: 1, page_size: 20, ban_type: 'manual' })
    expect(get).toHaveBeenCalledWith(
      '/ip-ban/bans',
      { page: 1, page_size: 20, ban_type: 'manual' },
      undefined
    )
  })

  it('banIpApi 发送封禁请求', async () => {
    const { banIpApi } = await import('@/lib/services/api/ipBan')
    const { post } = await import('@/lib/services/request')
    vi.mocked(post).mockResolvedValue({ id: 1, ip_or_cidr: '10.0.0.1' })
    const result = await banIpApi({ ip_or_cidr: '10.0.0.1', reason: 'test' })
    expect(post).toHaveBeenCalledWith(
      '/ip-ban/bans',
      { ip_or_cidr: '10.0.0.1', reason: 'test' },
      undefined
    )
    expect(result.ip_or_cidr).toBe('10.0.0.1')
  })

  it('batchUnbanApi 发送批量解封请求', async () => {
    const { batchUnbanApi } = await import('@/lib/services/api/ipBan')
    const { post } = await import('@/lib/services/request')
    vi.mocked(post).mockResolvedValue({ count: 2 })
    const result = await batchUnbanApi({ ban_ids: [1, 2] })
    expect(post).toHaveBeenCalledWith(
      '/ip-ban/bans/batch-unban',
      { ban_ids: [1, 2] },
      undefined
    )
    expect(result.count).toBe(2)
  })

  it('unbanIpApi 拼接 banId 到路径', async () => {
    const { unbanIpApi } = await import('@/lib/services/api/ipBan')
    const { post } = await import('@/lib/services/request')
    vi.mocked(post).mockResolvedValue({ id: 1, is_active: false })
    await unbanIpApi(1)
    expect(post).toHaveBeenCalledWith('/ip-ban/bans/1/unban', undefined, undefined)
  })

  it('getBanLogsApi 传递查询参数', async () => {
    const { getBanLogsApi } = await import('@/lib/services/api/ipBan')
    const { get } = await import('@/lib/services/request')
    vi.mocked(get).mockResolvedValue({ list: [], total: 0 })
    await getBanLogsApi({ page: 1, page_size: 10, action: 'ban' })
    expect(get).toHaveBeenCalledWith(
      '/ip-ban/logs',
      { page: 1, page_size: 10, action: 'ban' },
      undefined
    )
  })

  it('getBanRulesApi 获取规则列表', async () => {
    const { getBanRulesApi } = await import('@/lib/services/api/ipBan')
    const { get } = await import('@/lib/services/request')
    vi.mocked(get).mockResolvedValue([{ id: 'login_failure', enabled: true }])
    const result = await getBanRulesApi()
    expect(get).toHaveBeenCalledWith('/ip-ban/rules', undefined, undefined)
    expect(result).toHaveLength(1)
    expect(result[0].id).toBe('login_failure')
  })

  it('updateBanRuleApi 拼接 ruleId 到路径', async () => {
    const { updateBanRuleApi } = await import('@/lib/services/api/ipBan')
    const { put } = await import('@/lib/services/request')
    vi.mocked(put).mockResolvedValue({ id: 'login_failure', threshold: 5 })
    await updateBanRuleApi('login_failure', { threshold: 5 })
    expect(put).toHaveBeenCalledWith(
      '/ip-ban/rules/login_failure',
      { threshold: 5 },
      undefined
    )
  })

  it('getIpBanStatsApi 获取统计', async () => {
    const { getIpBanStatsApi } = await import('@/lib/services/api/ipBan')
    const { get } = await import('@/lib/services/request')
    vi.mocked(get).mockResolvedValue({ total_bans: 10, active_bans: 3 })
    const result = await getIpBanStatsApi()
    expect(get).toHaveBeenCalledWith('/ip-ban/stats', undefined, undefined)
    expect(result.total_bans).toBe(10)
  })
})