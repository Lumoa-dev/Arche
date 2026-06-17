import { describe, it, expect, vi, beforeEach } from 'vitest'

// Mock naive-ui useMessage
vi.mock('naive-ui', () => ({
  useMessage: () => ({
    warning: vi.fn(),
    success: vi.fn(),
    error: vi.fn()
  })
}))

// Mock API functions
const mockCreatePostApi = vi.fn()
const mockUpdatePostApi = vi.fn()
const mockGetPostByIdApi = vi.fn()

vi.mock('@/lib/services/api', () => ({
  getPostByIdApi: (...args: unknown[]) => mockGetPostByIdApi(...args),
  createPostApi: (...args: unknown[]) => mockCreatePostApi(...args),
  updatePostApi: (...args: unknown[]) => mockUpdatePostApi(...args)
}))

beforeEach(() => {
  vi.clearAllMocks()
})

describe('usePostEditor', () => {
  it('初始状态：新建模式', async () => {
    const { usePostEditor } = await import('@/components/widgets/create/usePostEditor')
    const editor = usePostEditor()

    expect(editor.postId.value).toBeNull()
    expect(editor.title.value).toBe('')
    expect(editor.content.value).toBe('')
    expect(editor.isEdit.value).toBe(false)
    expect(editor.loading.value).toBe(false)
    expect(editor.saving.value).toBe(false)
  })

  it('loadPost 正确填充 content 字段', async () => {
    const tipTapContent = JSON.stringify({
      type: 'doc',
      content: [{ type: 'paragraph', content: [{ type: 'text', text: 'Hello' }] }]
    })

    mockGetPostByIdApi.mockResolvedValue({
      id: 'post-1',
      title: '测试标题',
      content: tipTapContent,
      subtitles: [],
      cover_url: '',
      tags: ['tag1'],
      required_level: 5
    })

    const { usePostEditor } = await import('@/components/widgets/create/usePostEditor')
    const editor = usePostEditor()

    await editor.loadPost('post-1')

    expect(editor.postId.value).toBe('post-1')
    expect(editor.content.value).toBe(tipTapContent)
    expect(editor.title.value).toBe('测试标题')
    expect(editor.isEdit.value).toBe(true)
  })

  it('loadPost 处理 content 为空的情况', async () => {
    mockGetPostByIdApi.mockResolvedValue({
      id: 'post-2',
      title: '无内容',
      content: null,
      subtitles: [],
      cover_url: '',
      tags: [],
      required_level: 5
    })

    const { usePostEditor } = await import('@/components/widgets/create/usePostEditor')
    const editor = usePostEditor()

    await editor.loadPost('post-2')

    expect(editor.content.value).toBe('')
  })

  it('save 新建帖子时 content 字段被包含在 payload 中', async () => {
    const tipTapContent = JSON.stringify({
      type: 'doc',
      content: [{ type: 'paragraph', content: [{ type: 'text', text: '新内容' }] }]
    })

    mockCreatePostApi.mockResolvedValue({ id: 'new-post-1' })

    const { usePostEditor } = await import('@/components/widgets/create/usePostEditor')
    const editor = usePostEditor()

    editor.title.value = '新帖子'
    editor.content.value = tipTapContent

    await editor.save()

    expect(mockCreatePostApi).toHaveBeenCalledWith(
      expect.objectContaining({
        title: '新帖子',
        content: tipTapContent
      })
    )
  })

  it('save 编辑帖子时 content 字段被包含在 payload 中', async () => {
    const tipTapContent = JSON.stringify({
      type: 'doc',
      content: [{ type: 'paragraph', content: [{ type: 'text', text: '更新内容' }] }]
    })

    mockGetPostByIdApi.mockResolvedValue({
      id: 'edit-post-1',
      title: '旧标题',
      content: tipTapContent,
      subtitles: [],
      cover_url: '',
      tags: [],
      required_level: 5
    })
    mockUpdatePostApi.mockResolvedValue({ id: 'edit-post-1' })

    const { usePostEditor } = await import('@/components/widgets/create/usePostEditor')
    const editor = usePostEditor()
    await editor.loadPost('edit-post-1')

    // 修改 content
    const newContent = JSON.stringify({
      type: 'doc',
      content: [{ type: 'paragraph', content: [{ type: 'text', text: '更新后的内容' }] }]
    })
    editor.content.value = newContent

    await editor.save()

    expect(mockUpdatePostApi).toHaveBeenCalledWith(
      'edit-post-1',
      expect.objectContaining({
        content: newContent
      })
    )
  })

  it('save 新建帖子 content 为空时不发送 content 字段', async () => {
    mockCreatePostApi.mockResolvedValue({ id: 'post-no-content' })

    const { usePostEditor } = await import('@/components/widgets/create/usePostEditor')
    const editor = usePostEditor()

    editor.title.value = '无内容帖子'
    editor.content.value = ''

    await editor.save()

    // content 为 '' 是 falsy，所以 payload 中不应包含 content
    const payload = mockCreatePostApi.mock.calls[0][0]
    expect(payload).not.toHaveProperty('content')
  })

  it('resetForNew 重置所有状态', async () => {
    const { usePostEditor } = await import('@/components/widgets/create/usePostEditor')
    const editor = usePostEditor()

    // 先设置一些值
    editor.postId.value = 'post-1'
    editor.title.value = '标题'
    editor.content.value = '内容'
    editor.tags.value = ['tag1']

    editor.resetForNew()

    expect(editor.postId.value).toBeNull()
    expect(editor.title.value).toBe('')
    expect(editor.content.value).toBe('')
    expect(editor.tags.value).toEqual([])
    expect(editor.isEdit.value).toBe(false)
  })

  it('save 空标题不发送请求', async () => {
    const { usePostEditor } = await import('@/components/widgets/create/usePostEditor')
    const editor = usePostEditor()

    const result = await editor.save()

    expect(result).toBe(false)
    expect(mockCreatePostApi).not.toHaveBeenCalled()
  })
})