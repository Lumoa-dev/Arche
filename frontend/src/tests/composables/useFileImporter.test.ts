import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { useFileImporter } from '@/components/widgets/create/useFileImporter'

/**
 * 辅助函数：创建一个模拟 File 对象
 */
function createMockFile(name: string, content: string, mimeType = 'text/plain'): File {
  return new File([content], name, { type: mimeType })
}

describe('useFileImporter', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('初始状态：importing 为 false，importError 为 null', () => {
    const { importing, importError } = useFileImporter()
    expect(importing.value).toBe(false)
    expect(importError.value).toBeNull()
  })

  it('readFile 成功读取 .md 文件', async () => {
    const { readFile, importing } = useFileImporter()
    const file = createMockFile('test.md', '# Hello World\n\nThis is a test.')

    const result = await readFile(file)

    expect(result).not.toBeNull()
    expect(result!.text).toBe('# Hello World\n\nThis is a test.')
    expect(result!.fileName).toBe('test.md')
    // 读取完成后 importing 恢复为 false
    expect(importing.value).toBe(false)
  })

  it('readFile 成功读取 .txt 文件', async () => {
    const { readFile } = useFileImporter()
    const file = createMockFile('notes.txt', 'Plain text content.')

    const result = await readFile(file)

    expect(result).not.toBeNull()
    expect(result!.text).toBe('Plain text content.')
    expect(result!.fileName).toBe('notes.txt')
  })

  it('readFile 读取空文件返回 null 并设置错误信息', async () => {
    const { readFile, importError } = useFileImporter()

    const file = createMockFile('empty.md', '')
    const result = await readFile(file)

    expect(result).toBeNull()
    expect(importError.value).toBe('文件内容为空')
  })

  it('readFile 读取仅空白文件返回 null 并设置错误信息', async () => {
    const { readFile, importError } = useFileImporter()

    const file = createMockFile('spaces.txt', '   \n  \n  ')
    const result = await readFile(file)

    expect(result).toBeNull()
    expect(importError.value).toBe('文件内容为空')
  })

  it('readFile 读取过程中 importing 为 true', async () => {
    const { readFile, importing } = useFileImporter()

    const file = createMockFile('test.md', '# Content')
    // 用微任务队列来验证中间状态
    const promise = readFile(file)

    // 此时 importing 应为 true（同步设置）
    expect(importing.value).toBe(true)

    await promise
    expect(importing.value).toBe(false)
  })

  it('readFile 文件读取失败时返回 null 并设置错误信息', async () => {
    // 模拟 File.text() 抛出异常
    const file = createMockFile('broken.md', 'content')
    vi.spyOn(file, 'text').mockRejectedValue(new Error('File is corrupted'))

    const { readFile, importError } = useFileImporter()
    const result = await readFile(file)

    expect(result).toBeNull()
    expect(importError.value).toContain('文件读取失败')
    expect(importError.value).toContain('File is corrupted')
  })

  it('readFile 异常后 importing 恢复为 false', async () => {
    const file = createMockFile('broken.md', 'content')
    vi.spyOn(file, 'text').mockRejectedValue(new Error('error'))

    const { readFile, importing } = useFileImporter()
    await readFile(file)

    expect(importing.value).toBe(false)
  })

  it('importError 在每次 readFile 调用时重置', async () => {
    const { readFile, importError } = useFileImporter()

    // 第一次读取空文件，设置错误
    const emptyFile = createMockFile('empty.md', '')
    await readFile(emptyFile)
    expect(importError.value).toBe('文件内容为空')

    // 第二次读取正常文件，错误应被重置
    const goodFile = createMockFile('good.md', 'content')
    await readFile(goodFile)
    expect(importError.value).toBeNull()
  })
})