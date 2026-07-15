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
  it('getIpBansApi 分页查询', async () => {
    const { getIpBansApi } = await import('@/lib/services/api/ipBan')
    const { get } = await import('@/lib/services/request')
    vi.mocked(get).mockResolvedValue({ list: [], total: 0 })
    await getIpBansApi({ page: 1, pageSize: 20 })
    expect(get).toHaveBeenCalledWith('/ip-ban/bans', { page: 1, pageSize: 20 }, undefined)
  })

  it('banIpApi 发送 POST 封禁', async () => {
    const { banIpApi } = await import('@/lib/services/api/ipBan')
    const { post } = await import('@/lib/services/request')
    vi.mocked(post).mockResolvedValue({ id: 1, ip_or_cidr: '10.0.0.1' })
    const result = await banIpApi({ ip_or_cidr: '10.0.0.1', reason: 'spam' })
    expect(post).toHaveBeenCalledWith('/ip-ban/bans', { ip_or_cidr: '10.0.0.1', reason: 'spam' }, undefined)
    expect(result.ip_or_cidr).toBe('10.0.0.1')
  })

  it('batchUnbanApi 批量解封', async () => {
    const { batchUnbanApi } = await import('@/lib/services/api/ipBan')
    const { post } = await import('@/lib/services/request')
    vi.mocked(post).mockResolvedValue({ count: 2 })
    await batchUnbanApi({ ban_ids: [1, 2] })
    expect(post).toHaveBeenCalledWith('/ip-ban/bans/batch-unban', { ban_ids: [1, 2] }, undefined)
  })

  it('unbanIpApi 拼接 banId', async () => {
    const { unbanIpApi } = await import('@/lib/services/api/ipBan')
    const { post } = await import('@/lib/services/request')
    vi.mocked(post).mockResolvedValue({ id: 1 })
    await unbanIpApi(1)
    expect(post).toHaveBeenCalledWith('/ip-ban/bans/1/unban', undefined, undefined)
  })

  it('getBanLogsApi 查询封禁日志', async () => {
    const { getBanLogsApi } = await import('@/lib/services/api/ipBan')
    const { get } = await import('@/lib/services/request')
    vi.mocked(get).mockResolvedValue({ list: [], total: 0 })
    await getBanLogsApi({ action: 'ban', page: 1, pageSize: 20 })
    expect(get).toHaveBeenCalledWith('/ip-ban/logs', { action: 'ban', page: 1, pageSize: 20 }, undefined)
  })

  it('getBanRulesApi 获取规则列表', async () => {
    const { getBanRulesApi } = await import('@/lib/services/api/ipBan')
    const { get } = await import('@/lib/services/request')
    vi.mocked(get).mockResolvedValue([{ id: 'r1', name: 'Rule 1', enabled: true }])
    const result = await getBanRulesApi()
    expect(get).toHaveBeenCalledWith('/ip-ban/rules', undefined, undefined)
    expect(result).toHaveLength(1)
  })

  it('updateBanRuleApi 更新规则', async () => {
    const { updateBanRuleApi } = await import('@/lib/services/api/ipBan')
    const { put } = await import('@/lib/services/request')
    vi.mocked(put).mockResolvedValue({ id: 'r1', enabled: false })
    await updateBanRuleApi('r1', { enabled: false })
    expect(put).toHaveBeenCalledWith('/ip-ban/rules/r1', { enabled: false }, undefined)
  })

  it('getIpBanStatsApi 获取统计', async () => {
    const { getIpBanStatsApi } = await import('@/lib/services/api/ipBan')
    const { get } = await import('@/lib/services/request')
    vi.mocked(get).mockResolvedValue({ total_bans: 100, active_bans: 50 })
    const result = await getIpBanStatsApi()
    expect(get).toHaveBeenCalledWith('/ip-ban/stats', undefined, undefined)
    expect(result.total_bans).toBe(100)
  })
})