import { describe, it, expect, vi, beforeEach } from 'vitest'
import { usePostEditor } from '@/components/widgets/create/usePostEditor'

// mock naive-ui useMessage
vi.mock('naive-ui', () => ({
  useMessage: () => ({
    success: vi.fn(),
    warning: vi.fn(),
    error: vi.fn()
  })
}))

// mock API 调用
const mockGetPostByIdApi = vi.fn()
const mockCreatePostApi = vi.fn()
const mockUpdatePostApi = vi.fn()

vi.mock('@/lib/services/api', () => ({
  getPostByIdApi: (...args: any[]) => mockGetPostByIdApi(...args),
  createPostApi: (...args: any[]) => mockCreatePostApi(...args),
  updatePostApi: (...args: any[]) => mockUpdatePostApi(...args)
}))

describe('usePostEditor', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('初始状态：新建模式，所有字段为空', () => {
    const editor = usePostEditor()
    expect(editor.postId.value).toBeNull()
    expect(editor.title.value).toBe('')
    expect(editor.subtitles.value).toEqual([])
    expect(editor.coverUrl.value).toBe('')
    expect(editor.tags.value).toEqual([])
    expect(editor.requiredLevel.value).toBe(5)
    expect(editor.content.value).toBe('')
    expect(editor.loading.value).toBe(false)
    expect(editor.saving.value).toBe(false)
    expect(editor.isEdit.value).toBe(false)
  })

  it('resetForNew 重置所有状态为初始值', () => {
    const editor = usePostEditor()
    // 先设置一些值
    editor.title.value = '旧标题'
    editor.content.value = '旧内容'
    editor.tags.value = ['tag1']
    editor.coverUrl.value = 'http://example.com/cover.jpg'

    editor.resetForNew()

    expect(editor.postId.value).toBeNull()
    expect(editor.title.value).toBe('')
    expect(editor.subtitles.value).toEqual([])
    expect(editor.coverUrl.value).toBe('')
    expect(editor.tags.value).toEqual([])
    expect(editor.requiredLevel.value).toBe(5)
    expect(editor.content.value).toBe('')
    expect(editor.isEdit.value).toBe(false)
  })

  it('loadPost 从 API 加载帖子并映射所有字段', async () => {
    const mockPost = {
      id: 'post-123',
      title: '测试文章',
      subtitles: ['副标题1', '副标题2'],
      cover_url: 'https://example.com/cover.jpg',
      tags: ['vue', 'testing'],
      required_level: 3,
      content: '{"type":"doc","content":[]}'
    }
    mockGetPostByIdApi.mockResolvedValue(mockPost)

    const editor = usePostEditor()
    await editor.loadPost('post-123')

    expect(editor.postId.value).toBe('post-123')
    expect(editor.title.value).toBe('测试文章')
    expect(editor.subtitles.value).toEqual(['副标题1', '副标题2'])
    expect(editor.coverUrl.value).toBe('https://example.com/cover.jpg')
    expect(editor.tags.value).toEqual(['vue', 'testing'])
    expect(editor.requiredLevel.value).toBe(3)
    expect(editor.content.value).toBe('{"type":"doc","content":[]}')
    expect(editor.isEdit.value).toBe(true)
    expect(editor.loading.value).toBe(false)
  })

  it('loadPost 处理缺失字段使用默认值', async () => {
    const mockPost = { id: 'post-456', title: '最小文章' }
    mockGetPostByIdApi.mockResolvedValue(mockPost)

    const editor = usePostEditor()
    await editor.loadPost('post-456')

    expect(editor.title.value).toBe('最小文章')
    expect(editor.subtitles.value).toEqual([])
    expect(editor.coverUrl.value).toBe('')
    expect(editor.tags.value).toEqual([])
    expect(editor.requiredLevel.value).toBe(5)
    expect(editor.content.value).toBe('')
  })

  it('loadPost 中 loading 状态正确变化', async () => {
    let resolveFn!: (v: any) => void
    mockGetPostByIdApi.mockReturnValue(
      new Promise((resolve) => {
        resolveFn = resolve
      })
    )

    const editor = usePostEditor()
    const promise = editor.loadPost('post-789')
    expect(editor.loading.value).toBe(true)

    resolveFn({ id: 'post-789', title: '测试' })
    await promise
    expect(editor.loading.value).toBe(false)
  })

  it('save 阻止空标题提交', async () => {
    const editor = usePostEditor()
    editor.title.value = ''

    const result = await editor.save()

    expect(result).toBe(false)
    expect(mockCreatePostApi).not.toHaveBeenCalled()
    expect(mockUpdatePostApi).not.toHaveBeenCalled()
  })

  it('save 在新建模式下调用 createPostApi', async () => {
    const mockCreated = { id: 'new-post-id', title: '新文章' }
    mockCreatePostApi.mockResolvedValue(mockCreated)

    const editor = usePostEditor()
    editor.title.value = '新文章'
    editor.content.value = '{"type":"doc"}'
    editor.tags.value = ['tag1', 'tag2']
    editor.requiredLevel.value = 5

    const result = await editor.save()

    expect(result).toBe(true)
    expect(mockCreatePostApi).toHaveBeenCalledWith({
      title: '新文章',
      subtitles: [],
      tags: ['tag1', 'tag2'],
      required_level: 5,
      content: '{"type":"doc"}'
    })
    expect(editor.postId.value).toBe('new-post-id')
  })

  it('save 在编辑模式下调用 updatePostApi', async () => {
    mockUpdatePostApi.mockResolvedValue({ id: 'existing-id' })

    const editor = usePostEditor()
    editor.postId.value = 'existing-id'
    editor.title.value = '已编辑的文章'
    editor.content.value = '更新后的内容'

    const result = await editor.save()

    expect(result).toBe(true)
    expect(mockUpdatePostApi).toHaveBeenCalledWith('existing-id', {
      title: '已编辑的文章',
      subtitles: [],
      tags: [],
      required_level: 5,
      content: '更新后的内容'
    })
  })

  it('save 在编辑模式下保留 postId', async () => {
    mockUpdatePostApi.mockResolvedValue({ id: 'existing-id' })

    const editor = usePostEditor()
    editor.postId.value = 'existing-id'
    editor.title.value = '标题不变'

    await editor.save()

    expect(editor.postId.value).toBe('existing-id')
  })

  it('save 向 createPostApi 传递 cover_url', async () => {
    mockCreatePostApi.mockResolvedValue({ id: 'post-id' })

    const editor = usePostEditor()
    editor.title.value = '有封面的文章'
    editor.coverUrl.value = 'https://example.com/cover.jpg'

    await editor.save()

    expect(mockCreatePostApi).toHaveBeenCalledWith(
      expect.objectContaining({ cover_url: 'https://example.com/cover.jpg' })
    )
  })

  it('save 不传递空的 cover_url', async () => {
    mockCreatePostApi.mockResolvedValue({ id: 'post-id' })

    const editor = usePostEditor()
    editor.title.value = '无封面'

    await editor.save()

    const callArgs = mockCreatePostApi.mock.calls[0][0]
    expect(callArgs).not.toHaveProperty('cover_url')
  })

  it('save 过滤空副标题', async () => {
    mockCreatePostApi.mockResolvedValue({ id: 'post-id' })

    const editor = usePostEditor()
    editor.title.value = '文章'
    editor.subtitles.value = ['有效副标题', '', '  ', '另一个']

    await editor.save()

    expect(mockCreatePostApi).toHaveBeenCalledWith(
      expect.objectContaining({ subtitles: ['有效副标题', '另一个'] })
    )
  })

  it('save 在 API 失败时返回 false', async () => {
    mockCreatePostApi.mockRejectedValue(new Error('网络错误'))

    const editor = usePostEditor()
    editor.title.value = '会失败的文章'

    const result = await editor.save()

    expect(result).toBe(false)
  })

  it('save 中 saving 状态正确变化', async () => {
    let resolveFn!: (v: any) => void
    mockCreatePostApi.mockReturnValue(
      new Promise((resolve) => {
        resolveFn = resolve
      })
    )

    const editor = usePostEditor()
    editor.title.value = '测试'
    const promise = editor.save()
    expect(editor.saving.value).toBe(true)

    resolveFn({ id: 'test-id' })
    await promise
    expect(editor.saving.value).toBe(false)
  })

  it('loadPost 后 isEdit 为 true', async () => {
    mockGetPostByIdApi.mockResolvedValue({ id: 'p1', title: '已有文章' })

    const editor = usePostEditor()
    expect(editor.isEdit.value).toBe(false)

    await editor.loadPost('p1')

    expect(editor.isEdit.value).toBe(true)
  })

  it('resetForNew 后 isEdit 恢复为 false', async () => {
    mockGetPostByIdApi.mockResolvedValue({ id: 'p1', title: '已有文章' })

    const editor = usePostEditor()
    await editor.loadPost('p1')
    expect(editor.isEdit.value).toBe(true)

    editor.resetForNew()
    expect(editor.isEdit.value).toBe(false)
  })
})