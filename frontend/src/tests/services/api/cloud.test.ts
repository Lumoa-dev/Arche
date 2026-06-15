import { describe, it, expect, vi, beforeEach } from 'vitest'

vi.mock('@/lib/services/request', () => ({ get: vi.fn(), post: vi.fn(), del: vi.fn() }))
beforeEach(() => {
  vi.clearAllMocks()
})

describe('cloud API', () => {
  it('getCloudStatsApi', async () => {
    const { getCloudStatsApi } = await import('@/lib/services/api/cloud')
    const { get } = await import('@/lib/services/request')
    vi.mocked(get).mockResolvedValue({ running_jobs: 5, running_instances: 3 })
    await getCloudStatsApi()
    expect(get).toHaveBeenCalledWith('/cloud/stats', undefined, undefined)
  })

  it('getCloudJobsApi 传 status 参数', async () => {
    const { getCloudJobsApi } = await import('@/lib/services/api/cloud')
    const { get } = await import('@/lib/services/request')
    vi.mocked(get).mockResolvedValue({ items: [], total: 0 })
    await getCloudJobsApi({ status: 'running' })
    expect(get).toHaveBeenCalledWith('/cloud/jobs', { status: 'running' }, undefined)
  })

  it('getCloudJobDetailApi 拼接 jobId', async () => {
    const { getCloudJobDetailApi } = await import('@/lib/services/api/cloud')
    const { get } = await import('@/lib/services/request')
    vi.mocked(get).mockResolvedValue({ id: 'j1', name: 'test', status: 'running' })
    await getCloudJobDetailApi('j1')
    expect(get).toHaveBeenCalledWith('/cloud/jobs/j1', undefined, undefined)
  })

  it('createCloudJobApi', async () => {
    const { createCloudJobApi } = await import('@/lib/services/api/cloud')
    const { post } = await import('@/lib/services/request')
    vi.mocked(post).mockResolvedValue({ id: 'j1' })
    const payload = { name: 'test', repo_url: 'https://github.com/a/b' }
    await createCloudJobApi(payload)
    expect(post).toHaveBeenCalledWith('/cloud/jobs', payload, undefined)
  })

  it('deleteCloudJobApi', async () => {
    const { deleteCloudJobApi } = await import('@/lib/services/api/cloud')
    const { del } = await import('@/lib/services/request')
    vi.mocked(del).mockResolvedValue(undefined)
    await deleteCloudJobApi('j1')
    expect(del).toHaveBeenCalledWith('/cloud/jobs/j1', undefined, undefined)
  })

  it('startCloudJobApi 和 stopCloudJobApi', async () => {
    const { startCloudJobApi, stopCloudJobApi } = await import('@/lib/services/api/cloud')
    const { post } = await import('@/lib/services/request')
    vi.mocked(post).mockResolvedValue({ id: 'j1', status: 'running' })
    await startCloudJobApi('j1')
    expect(post).toHaveBeenCalledWith('/cloud/jobs/j1/start', undefined, undefined)
    await stopCloudJobApi('j1')
    expect(post).toHaveBeenCalledWith('/cloud/jobs/j1/stop', undefined, undefined)
  })

  it('getCloudJobLogsApi 传 lines 参数', async () => {
    const { getCloudJobLogsApi } = await import('@/lib/services/api/cloud')
    const { get } = await import('@/lib/services/request')
    vi.mocked(get).mockResolvedValue({ logs: ['line1'], total_lines: 1 })
    await getCloudJobLogsApi('j1', 50)
    expect(get).toHaveBeenCalledWith('/cloud/jobs/j1/logs', { lines: 50 }, undefined)
  })

  it('getCloudJobProgressApi', async () => {
    const { getCloudJobProgressApi } = await import('@/lib/services/api/cloud')
    const { get } = await import('@/lib/services/request')
    vi.mocked(get).mockResolvedValue({ job_id: 'j1', status: 'running' })
    await getCloudJobProgressApi('j1')
    expect(get).toHaveBeenCalledWith('/cloud/jobs/j1/progress', undefined, undefined)
  })

  it('listDatasetsApi', async () => {
    const { listDatasetsApi } = await import('@/lib/services/api/cloud')
    const { get } = await import('@/lib/services/request')
    vi.mocked(get).mockResolvedValue({ items: [], total: 0 })
    await listDatasetsApi({ source: 'local' })
    expect(get).toHaveBeenCalledWith('/cloud/datasets', { source: 'local' }, undefined)
  })

  it('createDatasetApi', async () => {
    const { createDatasetApi } = await import('@/lib/services/api/cloud')
    const { post } = await import('@/lib/services/request')
    vi.mocked(post).mockResolvedValue({ id: 'd1', name: 'ds' })
    const payload = { name: 'ds', path: 'datasets/ds' }
    await createDatasetApi(payload)
    expect(post).toHaveBeenCalledWith('/cloud/datasets', payload, undefined)
  })

  it('listReposApi', async () => {
    const { listReposApi } = await import('@/lib/services/api/cloud')
    const { get } = await import('@/lib/services/request')
    vi.mocked(get).mockResolvedValue({ items: [], total: 0 })
    await listReposApi()
    expect(get).toHaveBeenCalledWith('/cloud/repos', undefined, undefined)
  })

  it('listArtifactsApi', async () => {
    const { listArtifactsApi } = await import('@/lib/services/api/cloud')
    const { get } = await import('@/lib/services/request')
    vi.mocked(get).mockResolvedValue({ items: [], total: 0 })
    await listArtifactsApi({ artifact_type: 'log' })
    expect(get).toHaveBeenCalledWith('/cloud/artifacts', { artifact_type: 'log' }, undefined)
  })

  it('downloadArtifactApi', async () => {
    const { downloadArtifactApi } = await import('@/lib/services/api/cloud')
    const { get } = await import('@/lib/services/request')
    vi.mocked(get).mockResolvedValue({ download_url: 'https://example.com/art' })
    await downloadArtifactApi('a1')
    expect(get).toHaveBeenCalledWith('/cloud/artifacts/a1/download', undefined, undefined)
  })
})
