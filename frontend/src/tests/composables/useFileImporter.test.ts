import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useFileImporter } from '@/components/widgets/create/useFileImporter'

/**
 * 辅助函数：创建模拟 File 对象
 */
function createMockFile(
  name: string,
  content: string,
  mimeType = 'text/plain'
): File {
  return new File([content], name, { type: mimeType })
}

describe('useFileImporter', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('初始状态：importing 为 false，importError 为 null', () => {
    const importer = useFileImporter()

    expect(importer.importing.value).toBe(false)
    expect(importer.importError.value).toBeNull()
  })

  it('readFile 成功读取文本内容', async () => {
    const importer = useFileImporter()
    const file = createMockFile('test.md', '# Hello World\nThis is a test.')

    const result = await importer.readFile(file)

    expect(result).not.toBeNull()
    expect(result!.text).toBe('# Hello World\nThis is a test.')
    expect(result!.fileName).toBe('test.md')
    expect(importer.importing.value).toBe(false)
    expect(importer.importError.value).toBeNull()
  })

  it('readFile 读取空文件返回 null', async () => {
    const importer = useFileImporter()
    const file = createMockFile('empty.md', '   ')

    const result = await importer.readFile(file)

    expect(result).toBeNull()
    expect(importer.importError.value).toBe('文件内容为空')
  })

  it('readFile 读取完全空文件返回 null', async () => {
    const importer = useFileImporter()
    const file = createMockFile('empty.txt', '')

    const result = await importer.readFile(file)

    expect(result).toBeNull()
    expect(importer.importError.value).toBe('文件内容为空')
  })

  it('readFile 读取失败时设置错误信息', async () => {
    const importer = useFileImporter()
    const file = createMockFile('broken.md', 'content')

    // 模拟 file.text() 抛出异常
    vi.spyOn(file, 'text').mockRejectedValue(new Error('File read error'))

    const result = await importer.readFile(file)

    expect(result).toBeNull()
    expect(importer.importError.value).toContain('文件读取失败')
    expect(importer.importing.value).toBe(false)
  })

  it('readFile 读取 .txt 文件', async () => {
    const importer = useFileImporter()
    const file = createMockFile('notes.txt', 'Some plain text')

    const result = await importer.readFile(file)

    expect(result).not.toBeNull()
    expect(result!.text).toBe('Some plain text')
    expect(result!.fileName).toBe('notes.txt')
  })

  it('readFile 读取 .html 文件', async () => {
    const importer = useFileImporter()
    const file = createMockFile('page.html', '<p>HTML content</p>', 'text/html')

    const result = await importer.readFile(file)

    expect(result).not.toBeNull()
    expect(result!.text).toBe('<p>HTML content</p>')
  })

  it('pickAndRead 创建文件选择器并返回 Promise', () => {
    const importer = useFileImporter()

    // 验证 pickAndRead 返回一个 Promise
    const result = importer.pickAndRead()
    expect(result).toBeInstanceOf(Promise)
  })

  it('readFile 过程中 importing 状态正确', async () => {
    const importer = useFileImporter()
    const file = createMockFile('test.md', 'content')

    // 创建延迟解析的 Promise 来观察中间状态
    const slowPromise = new Promise<string>((resolve) =>
      setTimeout(() => resolve('delayed content'), 50)
    )
    vi.spyOn(file, 'text').mockReturnValue(slowPromise)

    const readPromise = importer.readFile(file)

    // 读取过程中 importing 为 true
    expect(importer.importing.value).toBe(true)

    await readPromise

    // 读取完成后 importing 为 false
    expect(importer.importing.value).toBe(false)
  })
})