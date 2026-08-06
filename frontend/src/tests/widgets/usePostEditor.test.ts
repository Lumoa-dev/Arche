/**
 * usePostEditor 单元测试
 *
 * 测试原则：
 * - 使用 vitest mock 隔离 API 调用
 * - 每个测试独立，不依赖执行顺序
 * - 覆盖编辑器核心生命周期：初始化 → 加载 → 编辑 → 保存
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { usePostEditor } from '@/components/widgets/create/usePostEditor'

// ── Mock API 模块 ──
vi.mock('@/lib/services/api', () => ({
  getPostByIdApi: vi.fn(),
  createPostApi: vi.fn(),
  updatePostApi: vi.fn()
}))

// ── Mock naive-ui message ──
vi.mock('naive-ui', () => ({
  useMessage: () => ({
    success: vi.fn(),
    warning: vi.fn(),
    error: vi.fn()
  })
}))

import { getPostByIdApi, createPostApi, updatePostApi } from '@/lib/services/api'

describe('usePostEditor', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  // ── 初始状态 ──

  it('初始状态：所有字段为空，isEdit 为 false', () => {
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

  // ── resetForNew ──

  it('resetForNew() 将所有字段恢复为初始值', () => {
    const editor = usePostEditor()

    // 先设置一些值
    editor.postId.value = '123'
    editor.title.value = '旧标题'
    editor.subtitles.value = ['副标题']
    editor.content.value = '旧内容'
    editor.coverUrl.value = 'http://example.com/cover.jpg'
    editor.tags.value = ['tag1']
    editor.requiredLevel.value = 3

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

  // ── loadPost ──

  it('loadPost() 从 API 加载帖子并填充字段', async () => {
    const mockPost = {
      id: 'post-123',
      title: '测试标题',
      subtitles: ['副标题1'],
      cover_url: 'http://example.com/cover.jpg',
      tags: ['tag1', 'tag2'],
      required_level: 3,
      content: '{"type":"doc","content":[]}'
    }
    vi.mocked(getPostByIdApi).mockResolvedValue(mockPost)

    const editor = usePostEditor()
    await editor.loadPost('post-123')

    expect(editor.postId.value).toBe('post-123')
    expect(editor.title.value).toBe('测试标题')
    expect(editor.subtitles.value).toEqual(['副标题1'])
    expect(editor.coverUrl.value).toBe('http://example.com/cover.jpg')
    expect(editor.tags.value).toEqual(['tag1', 'tag2'])
    expect(editor.requiredLevel.value).toBe(3)
    expect(editor.content.value).toBe('{"type":"doc","content":[]}')
    expect(editor.isEdit.value).toBe(true)
    expect(editor.loading.value).toBe(false)
  })

  it('loadPost() 加载过程中 loading 为 true', async () => {
    let resolvePromise: (value: any) => void
    const promise = new Promise((resolve) => {
      resolvePromise = resolve
    })
    vi.mocked(getPostByIdApi).mockReturnValue(promise as any)

    const editor = usePostEditor()
    const loadPromise = editor.loadPost('post-123')

    expect(editor.loading.value).toBe(true)

    resolvePromise!({
      id: 'post-123',
      title: '标题',
      subtitles: [],
      tags: [],
      required_level: 5
    })

    await loadPromise
    expect(editor.loading.value).toBe(false)
  })

  it('loadPost() API 失败时显示错误但不影响编辑器状态', async () => {
    vi.mocked(getPostByIdApi).mockRejectedValue(new Error('网络错误'))

    const editor = usePostEditor()
    editor.title.value = '已有标题'
    await editor.loadPost('post-999')

    // 加载失败后，已有字段不应被覆盖（因为 catch 块中未设置）
    // 但 postId 不会被设置
    expect(editor.postId.value).toBeNull()
    expect(editor.loading.value).toBe(false)
  })

  it('loadPost() 处理空值字段', async () => {
    const mockPost = {
      id: 'post-456',
      title: null,
      subtitles: null,
      cover_url: null,
      tags: null,
      required_level: null,
      content: null
    }
    vi.mocked(getPostByIdApi).mockResolvedValue(mockPost)

    const editor = usePostEditor()
    await editor.loadPost('post-456')

    // 空值应回退到空字符串/空数组
    expect(editor.title.value).toBe('')
    expect(editor.subtitles.value).toEqual([])
    expect(editor.coverUrl.value).toBe('')
    expect(editor.tags.value).toEqual([])
    expect(editor.requiredLevel.value).toBe(5)
    expect(editor.content.value).toBe('')
  })

  // ── save（新建） ──

  it('save() 新建帖子时标题为空返回 false', async () => {
    const editor = usePostEditor()
    editor.title.value = ''

    const result = await editor.save()

    expect(result).toBe(false)
    expect(createPostApi).not.toHaveBeenCalled()
  })

  it('save() 新建帖子时标题仅含空白字符返回 false', async () => {
    const editor = usePostEditor()
    editor.title.value = '   '

    const result = await editor.save()

    expect(result).toBe(false)
    expect(createPostApi).not.toHaveBeenCalled()
  })

  it('save() 新建帖子成功调用 createPostApi', async () => {
    vi.mocked(createPostApi).mockResolvedValue({ id: 'new-post-1' })

    const editor = usePostEditor()
    editor.title.value = '新帖子标题'
    editor.subtitles.value = ['副标题']
    editor.tags.value = ['tag1']
    editor.content.value = '{"type":"doc"}'

    const result = await editor.save()

    expect(result).toBe(true)
    expect(createPostApi).toHaveBeenCalledWith({
      title: '新帖子标题',
      subtitles: ['副标题'],
      tags: ['tag1'],
      required_level: 5,
      content: '{"type":"doc"}'
    })
    expect(editor.postId.value).toBe('new-post-1')
    expect(editor.saving.value).toBe(false)
  })

  it('save() 新建帖子时过滤空副标题', async () => {
    vi.mocked(createPostApi).mockResolvedValue({ id: 'new-post-2' })

    const editor = usePostEditor()
    editor.title.value = '标题'
    editor.subtitles.value = ['有效副标题', '', '  ']

    await editor.save()

    expect(createPostApi).toHaveBeenCalledWith(
      expect.objectContaining({
        subtitles: ['有效副标题']
      })
    )
  })

  it('save() 新建帖子时 coverUrl 为空不包含在 payload 中', async () => {
    vi.mocked(createPostApi).mockResolvedValue({ id: 'new-post-3' })

    const editor = usePostEditor()
    editor.title.value = '标题'
    editor.coverUrl.value = ''

    await editor.save()

    const payload = vi.mocked(createPostApi).mock.calls[0][0]
    expect(payload).not.toHaveProperty('cover_url')
  })

  it('save() 新建帖子时 coverUrl 存在包含在 payload 中', async () => {
    vi.mocked(createPostApi).mockResolvedValue({ id: 'new-post-4' })

    const editor = usePostEditor()
    editor.title.value = '标题'
    editor.coverUrl.value = 'http://example.com/cover.jpg'

    await editor.save()

    const payload = vi.mocked(createPostApi).mock.calls[0][0]
    expect(payload).toHaveProperty('cover_url', 'http://example.com/cover.jpg')
  })

  // ── save（编辑） ──

  it('save() 编辑帖子时调用 updatePostApi', async () => {
    vi.mocked(updatePostApi).mockResolvedValue(undefined)

    const editor = usePostEditor()
    editor.postId.value = 'edit-post-1'
    editor.title.value = '编辑后的标题'
    editor.content.value = '{"type":"doc","content":[]}'

    const result = await editor.save()

    expect(result).toBe(true)
    expect(updatePostApi).toHaveBeenCalledWith('edit-post-1', {
      title: '编辑后的标题',
      subtitles: [],
      tags: [],
      required_level: 5,
      content: '{"type":"doc","content":[]}'
    })
  })

  it('save() 编辑时 isEdit 为 true', async () => {
    vi.mocked(updatePostApi).mockResolvedValue(undefined)

    const editor = usePostEditor()
    editor.postId.value = 'edit-post-2'
    editor.title.value = '标题'

    await editor.save()

    expect(editor.isEdit.value).toBe(true)
  })

  // ── save（错误处理） ──

  it('save() API 失败时返回 false', async () => {
    vi.mocked(createPostApi).mockRejectedValue(new Error('创建失败'))

    const editor = usePostEditor()
    editor.title.value = '标题'

    const result = await editor.save()

    expect(result).toBe(false)
    expect(editor.saving.value).toBe(false)
  })

  it('save() 过程中 saving 状态正确切换', async () => {
    let resolvePromise: (value: any) => void
    const promise = new Promise((resolve) => {
      resolvePromise = resolve
    })
    vi.mocked(createPostApi).mockReturnValue(promise as any)

    const editor = usePostEditor()
    editor.title.value = '标题'

    const savePromise = editor.save()
    expect(editor.saving.value).toBe(true)

    resolvePromise!({ id: 'new-post' })
    await savePromise
    expect(editor.saving.value).toBe(false)
  })
})