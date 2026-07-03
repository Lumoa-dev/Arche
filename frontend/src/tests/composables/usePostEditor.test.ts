import { describe, it, expect, vi, beforeEach } from 'vitest'
import { usePostEditor } from '@/components/widgets/create/usePostEditor'

// Mock naive-ui useMessage
vi.mock('naive-ui', () => ({
  useMessage: () => ({
    success: vi.fn(),
    warning: vi.fn(),
    error: vi.fn()
  })
}))

// Mock API
vi.mock('@/lib/services/api', () => ({
  getPostByIdApi: vi.fn(),
  createPostApi: vi.fn(),
  updatePostApi: vi.fn()
}))

beforeEach(() => {
  vi.clearAllMocks()
})

describe('usePostEditor', () => {
  it('初始状态：postId 为 null，内容为空，loading 为 false', () => {
    const editor = usePostEditor()

    expect(editor.postId.value).toBeNull()
    expect(editor.title.value).toBe('')
    expect(editor.subtitles.value).toEqual([])
    expect(editor.content.value).toBe('')
    expect(editor.coverUrl.value).toBe('')
    expect(editor.tags.value).toEqual([])
    expect(editor.requiredLevel.value).toBe(5)
    expect(editor.loading.value).toBe(false)
    expect(editor.saving.value).toBe(false)
    expect(editor.isEdit.value).toBe(false)
  })

  it('resetForNew 重置所有状态', () => {
    const editor = usePostEditor()

    // 先设置一些值
    editor.title.value = 'Test Title'
    editor.subtitles.value = ['Sub']
    editor.content.value = 'Content'
    editor.postId.value = 'post-123'

    // 重置
    editor.resetForNew()

    expect(editor.postId.value).toBeNull()
    expect(editor.title.value).toBe('')
    expect(editor.subtitles.value).toEqual([])
    expect(editor.content.value).toBe('')
    expect(editor.coverUrl.value).toBe('')
    expect(editor.tags.value).toEqual([])
    expect(editor.requiredLevel.value).toBe(5)
    expect(editor.isEdit.value).toBe(false)
  })

  it('loadPost 加载帖子到编辑器', async () => {
    const { getPostByIdApi } = await import('@/lib/services/api')
    const mockPost = {
      id: 'post-1',
      title: 'Test Post',
      subtitles: ['Sub 1', 'Sub 2'],
      cover_url: 'https://example.com/cover.jpg',
      tags: ['tag1', 'tag2'],
      required_level: 3,
      content: '{"type":"doc","content":[]}'
    }
    vi.mocked(getPostByIdApi).mockResolvedValue(mockPost)

    const editor = usePostEditor()
    await editor.loadPost('post-1')

    expect(editor.postId.value).toBe('post-1')
    expect(editor.title.value).toBe('Test Post')
    expect(editor.subtitles.value).toEqual(['Sub 1', 'Sub 2'])
    expect(editor.coverUrl.value).toBe('https://example.com/cover.jpg')
    expect(editor.tags.value).toEqual(['tag1', 'tag2'])
    expect(editor.requiredLevel.value).toBe(3)
    expect(editor.content.value).toBe('{"type":"doc","content":[]}')
    expect(editor.isEdit.value).toBe(true)
  })

  it('loadPost 加载失败时设置 error 提示', async () => {
    const { getPostByIdApi } = await import('@/lib/services/api')
    vi.mocked(getPostByIdApi).mockRejectedValue(new Error('Network error'))

    const editor = usePostEditor()
    await editor.loadPost('post-1')

    // loading 应恢复为 false
    expect(editor.loading.value).toBe(false)
    expect(editor.postId.value).toBeNull()
  })

  it('save 空标题返回 false', async () => {
    const editor = usePostEditor()
    editor.title.value = ''

    const result = await editor.save()
    expect(result).toBe(false)
  })

  it('save 新建帖子调用 createPostApi', async () => {
    const { createPostApi } = await import('@/lib/services/api')
    vi.mocked(createPostApi).mockResolvedValue({ id: 'new-post-1' })

    const editor = usePostEditor()
    editor.title.value = 'New Post'
    editor.subtitles.value = ['Sub']
    editor.tags.value = ['tag1']
    editor.content.value = '{"type":"doc"}'

    const result = await editor.save()
    expect(result).toBe(true)
    expect(createPostApi).toHaveBeenCalledWith({
      title: 'New Post',
      subtitles: ['Sub'],
      tags: ['tag1'],
      required_level: 5,
      content: '{"type":"doc"}'
    })
    expect(editor.postId.value).toBe('new-post-1')
  })

  it('save 更新帖子调用 updatePostApi', async () => {
    const { updatePostApi } = await import('@/lib/services/api')
    vi.mocked(updatePostApi).mockResolvedValue({ id: 'post-1' })

    const editor = usePostEditor()
    editor.postId.value = 'post-1'
    editor.title.value = 'Updated Title'
    editor.content.value = '{"type":"doc"}'

    const result = await editor.save()
    expect(result).toBe(true)
    expect(updatePostApi).toHaveBeenCalledWith('post-1', {
      title: 'Updated Title',
      subtitles: [],
      tags: [],
      required_level: 5,
      content: '{"type":"doc"}'
    })
  })

  it('save 过滤空副标题', async () => {
    const { createPostApi } = await import('@/lib/services/api')
    vi.mocked(createPostApi).mockResolvedValue({ id: 'new-post-1' })

    const editor = usePostEditor()
    editor.title.value = 'Test'
    editor.subtitles.value = ['Valid', '', '  ']

    await editor.save()

    // 空副标题应被过滤掉
    const payload = vi.mocked(createPostApi).mock.calls[0][0]
    expect(payload.subtitles).toEqual(['Valid'])
  })
})