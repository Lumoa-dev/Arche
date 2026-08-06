/**
 * useFileImporter 单元测试
 *
 * 测试原则：
 * - 使用 vitest mock 隔离 File API
 * - 覆盖文件读取成功、失败、空文件等场景
 * - 每个测试独立
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useFileImporter } from '@/components/widgets/create/useFileImporter'

describe('useFileImporter', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  // ── 初始状态 ──

  it('初始状态：importing 为 false，importError 为 null', () => {
    const importer = useFileImporter()

    expect(importer.importing.value).toBe(false)
    expect(importer.importError.value).toBeNull()
  })

  // ── readFile ──

  it('readFile() 成功读取文件内容', async () => {
    const file = new File(['# Hello World\n\nThis is content.'], 'test.md', {
      type: 'text/markdown'
    })

    const importer = useFileImporter()
    const result = await importer.readFile(file)

    expect(result).toEqual({
      text: '# Hello World\n\nThis is content.',
      fileName: 'test.md'
    })
    expect(importer.importing.value).toBe(false)
    expect(importer.importError.value).toBeNull()
  })

  it('readFile() 读取空文件返回 null', async () => {
    const file = new File([''], 'empty.md', { type: 'text/markdown' })

    const importer = useFileImporter()
    const result = await importer.readFile(file)

    expect(result).toBeNull()
    expect(importer.importError.value).toBe('文件内容为空')
  })

  it('readFile() 读取仅含空白字符的文件返回 null', async () => {
    const file = new File(['   \n  \t  '], 'whitespace.md', { type: 'text/markdown' })

    const importer = useFileImporter()
    const result = await importer.readFile(file)

    expect(result).toBeNull()
    expect(importer.importError.value).toBe('文件内容为空')
  })

  it('readFile() 读取过程中 importing 为 true', async () => {
    const importer = useFileImporter()

    // 使用 Blob 的 text() 方法返回 promise
    const blob = new Blob(['content'], { type: 'text/plain' })
    const file = new File([blob], 'test.txt')

    // 追踪 importing 状态变化
    const readPromise = importer.readFile(file)
    expect(importer.importing.value).toBe(true)

    await readPromise
    expect(importer.importing.value).toBe(false)
  })

  it('readFile() 文件读取失败时返回 null 并设置错误信息', async () => {
    const file = new File(['content'], 'test.txt')

    // Mock FileReader 的 text() 方法抛出异常
    const originalFileReader = File.prototype.text

    // 使用一个无法读取的 file 对象
    const badFile = new File(['content'], 'bad.txt')

    // 模拟 text() 方法失败
    vi.spyOn(badFile, 'text').mockRejectedValue(new Error('File is corrupted'))

    const importer = useFileImporter()
    const result = await importer.readFile(badFile)

    expect(result).toBeNull()
    expect(importer.importError.value).toContain('文件读取失败')
    expect(importer.importError.value).toContain('File is corrupted')
  })

  it('readFile() 读取大文件正常返回', async () => {
    const largeContent = 'x'.repeat(100000) // 100KB
    const file = new File([largeContent], 'large.txt', { type: 'text/plain' })

    const importer = useFileImporter()
    const result = await importer.readFile(file)

    expect(result).not.toBeNull()
    expect(result!.text).toHaveLength(100000)
    expect(result!.fileName).toBe('large.txt')
  })

  // ── pickAndRead ──

  it('pickAndRead() 用户取消选择时返回 null', async () => {
    // 模拟用户取消文件选择
    const inputMock = {
      type: 'file',
      accept: '.md,.txt,.markdown,.html',
      click: vi.fn(),
      onchange: null as any
    }

    const createElement = document.createElement.bind(document)
    vi.spyOn(document, 'createElement').mockImplementation((tagName, options) => {
      const el = createElement(tagName, options)
      if (tagName === 'input') {
        // 立即触发 onchange 且没有文件
        setTimeout(() => {
          if (inputMock.onchange) {
            inputMock.onchange({ target: { files: [] } })
          }
        }, 0)
        return inputMock as any
      }
      return el
    })

    const importer = useFileImporter()
    const result = await importer.pickAndRead()

    expect(result).toBeNull()
  })
})