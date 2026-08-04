import { describe, it, expect, vi, beforeEach } from 'vitest'
import { usePostEditor } from '@/components/widgets/create/usePostEditor'

// Mock API 模块
vi.mock('@/lib/services/api', () => ({
  getPostByIdApi: vi.fn(),
  createPostApi: vi.fn(),
  updatePostApi: vi.fn(),
}))

// Mock naive-ui useMessage
vi.mock('naive-ui', () => ({
  useMessage: () => ({
    error: vi.fn(),
    warning: vi.fn(),
    success: vi.fn(),
  }),
}))

import { getPostByIdApi, createPostApi, updatePostApi } from '@/lib/services/api'

describe('usePostEditor', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('初始状态：新建模式，所有字段为空', () => {
    const editor = usePostEditor()

    expect(editor.postId.value).toBeNull()
    expect(editor.isEdit.value).toBe(false)
    expect(editor.title.value).toBe('')
    expect(editor.subtitles.value).toEqual([])
    expect(editor.coverUrl.value).toBe('')
    expect(editor.tags.value).toEqual([])
    expect(editor.requiredLevel.value).toBe(5)
    expect(editor.content.value).toBe('')
    expect(editor.loading.value).toBe(false)
    expect(editor.saving.value).toBe(false)
  })

  it('resetForNew 重置所有字段到初始值', () => {
    const editor = usePostEditor()

    // 先设置一些值
    editor.title.value = 'Test Title'
    editor.subtitles.value = ['Sub1']
    editor.coverUrl.value = 'https://example.com/cover.jpg'
    editor.tags.value = ['tag1']
    editor.requiredLevel.value = 0
    editor.content.value = '{"type":"doc"}'

    editor.resetForNew()

    expect(editor.postId.value).toBeNull()
    expect(editor.isEdit.value).toBe(false)
    expect(editor.title.value).toBe('')
    expect(editor.subtitles.value).toEqual([])
    expect(editor.coverUrl.value).toBe('')
    expect(editor.tags.value).toEqual([])
    expect(editor.requiredLevel.value).toBe(5)
    expect(editor.content.value).toBe('')
  })

  it('loadPost 加载帖子到编辑器', async () => {
    const mockPost = {
      id: 'post-123',
      title: 'Loaded Post',
      subtitles: ['Subtitle 1'],
      cover_url: 'https://example.com/cover.jpg',
      tags: ['vue', 'typescript'],
      required_level: 3,
      content: '{"type":"doc","content":[]}',
    }
    vi.mocked(getPostByIdApi).mockResolvedValue(mockPost)

    const editor = usePostEditor()
    await editor.loadPost('post-123')

    expect(editor.postId.value).toBe('post-123')
    expect(editor.isEdit.value).toBe(true)
    expect(editor.title.value).toBe('Loaded Post')
    expect(editor.subtitles.value).toEqual(['Subtitle 1'])
    expect(editor.coverUrl.value).toBe('https://example.com/cover.jpg')
    expect(editor.tags.value).toEqual(['vue', 'typescript'])
    expect(editor.requiredLevel.value).toBe(3)
    expect(editor.content.value).toBe('{"type":"doc","content":[]}')
    expect(editor.loading.value).toBe(false)
  })

  it('loadPost 加载失败时 error 提示', async () => {
    vi.mocked(getPostByIdApi).mockRejectedValue(new Error('Network error'))

    const editor = usePostEditor()
    await editor.loadPost('post-999')

    // loading 状态应重置
    expect(editor.loading.value).toBe(false)
    // API 应被调用
    expect(getPostByIdApi).toHaveBeenCalledWith('post-999')
  })

  it('save 创建新帖子成功', async () => {
    const mockCreated = { id: 'new-post-1' }
    vi.mocked(createPostApi).mockResolvedValue(mockCreated)

    const editor = usePostEditor()
    editor.title.value = 'New Post'
    editor.subtitles.value = ['Sub1', '  ', 'Sub2']
    editor.tags.value = ['tag1']
    editor.requiredLevel.value = 3
    editor.coverUrl.value = 'https://example.com/cover.jpg'
    editor.content.value = '{"type":"doc"}'

    const result = await editor.save()

    expect(result).toBe(true)
    expect(editor.postId.value).toBe('new-post-1')
    expect(editor.isEdit.value).toBe(true)
    expect(createPostApi).toHaveBeenCalledWith({
      title: 'New Post',
      subtitles: ['Sub1', 'Sub2'],
      tags: ['tag1'],
      required_level: 3,
      cover_url: 'https://example.com/cover.jpg',
      content: '{"type":"doc"}',
    })
  })

  it('save 更新已有帖子成功', async () => {
    vi.mocked(updatePostApi).mockResolvedValue(undefined)

    const editor = usePostEditor()
    editor.postId.value = 'post-456'
    editor.title.value = 'Updated Post'

    const result = await editor.save()

    expect(result).toBe(true)
    expect(updatePostApi).toHaveBeenCalledWith('post-456', {
      title: 'Updated Post',
      subtitles: [],
      tags: [],
      required_level: 5,
    })
  })

  it('save 空标题时提示警告并返回 false', async () => {
    const editor = usePostEditor()
    editor.title.value = '  '

    const result = await editor.save()

    expect(result).toBe(false)
    expect(createPostApi).not.toHaveBeenCalled()
    expect(updatePostApi).not.toHaveBeenCalled()
  })

  it('save 创建失败时返回 false', async () => {
    vi.mocked(createPostApi).mockRejectedValue(new Error('创建失败'))

    const editor = usePostEditor()
    editor.title.value = 'New Post'

    const result = await editor.save()

    expect(result).toBe(false)
    expect(editor.saving.value).toBe(false)
  })

  it('save 更新失败时返回 false', async () => {
    vi.mocked(updatePostApi).mockRejectedValue(new Error('更新失败'))

    const editor = usePostEditor()
    editor.postId.value = 'post-789'
    editor.title.value = 'Failed Update'

    const result = await editor.save()

    expect(result).toBe(false)
    expect(editor.saving.value).toBe(false)
  })

  it('save 创建时传递空内容字段', async () => {
    vi.mocked(createPostApi).mockResolvedValue({ id: 'post-1' })

    const editor = usePostEditor()
    editor.title.value = 'Minimal Post'

    await editor.save()

    expect(createPostApi).toHaveBeenCalledWith({
      title: 'Minimal Post',
      subtitles: [],
      tags: [],
      required_level: 5,
    })
  })
})