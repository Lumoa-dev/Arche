import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useFileImporter } from '@/components/widgets/create/useFileImporter'

/**
 * 辅助：创建模拟 File 对象
 */
function createMockFile(
  content: string,
  name: string = 'test.md',
  mime: string = 'text/plain'
): File {
  const blob = new Blob([content], { type: mime })
  return new File([blob], name)
}

describe('useFileImporter', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('初始状态：未导入、无错误', () => {
    const importer = useFileImporter()
    expect(importer.importing.value).toBe(false)
    expect(importer.importError.value).toBeNull()
  })

  it('readFile 成功读取文本文件内容', async () => {
    const importer = useFileImporter()
    const file = createMockFile('# Hello World\n\nThis is content.', 'hello.md')

    const result = await importer.readFile(file)

    expect(result).not.toBeNull()
    expect(result!.text).toBe('# Hello World\n\nThis is content.')
    expect(result!.fileName).toBe('hello.md')
    expect(importer.importError.value).toBeNull()
  })

  it('readFile 读取空文件时返回 null 并设置错误', async () => {
    const importer = useFileImporter()
    const file = createMockFile('', 'empty.md')

    const result = await importer.readFile(file)

    expect(result).toBeNull()
    expect(importer.importError.value).toBe('文件内容为空')
  })

  it('readFile 读取只含空白符的文件时返回 null', async () => {
    const importer = useFileImporter()
    const file = createMockFile('   \n  \n  ', 'whitespace.md')

    const result = await importer.readFile(file)

    expect(result).toBeNull()
    expect(importer.importError.value).toBe('文件内容为空')
  })

  it('readFile 处理 file.text() 抛出的异常', async () => {
    const importer = useFileImporter()
    const badFile = createMockFile('content', 'bad.txt')
    // 篡改 text() 方法使其抛出异常
    vi.spyOn(badFile, 'text').mockRejectedValue(new Error('文件损坏'))

    const result = await importer.readFile(badFile)

    expect(result).toBeNull()
    expect(importer.importError.value).toContain('文件读取失败')
  })

  it('readFile 过程中 importing 为 true', async () => {
    let resolveFn!: (v: string) => void
    const importer = useFileImporter()
    const file = createMockFile('content', 'test.txt')

    // 让 text() 返回一个可控的 Promise
    vi.spyOn(file, 'text').mockReturnValue(
      new Promise((resolve) => {
        resolveFn = resolve
      })
    )

    const promise = importer.readFile(file)
    expect(importer.importing.value).toBe(true)

    resolveFn('final content')
    await promise
    expect(importer.importing.value).toBe(false)
  })

  it('pickAndRead 在用户取消选择时返回 null', async () => {
    const importer = useFileImporter()
    // 模拟 document.createElement('input') 返回的元素没有 .click()
    const mockInput = document.createElement('input')
    const createElementSpy = vi
      .spyOn(document, 'createElement')
      .mockReturnValue(mockInput)

    // 触发 onchange 时 files 为 null
    const promise = importer.pickAndRead()

    // 触发 onchange
    const input = createElementSpy.mock.results[0].value as HTMLInputElement
    input.onchange?.(new Event('change'))

    const result = await promise
    expect(result).toBeNull()
    createElementSpy.mockRestore()
  })

  it('readFile 读取 HTML 文件返回原始内容', async () => {
    const importer = useFileImporter()
    const html = '<h1>Title</h1><p>Content</p>'
    const file = createMockFile(html, 'page.html', 'text/html')

    const result = await importer.readFile(file)

    expect(result).not.toBeNull()
    expect(result!.text).toBe(html)
    expect(result!.fileName).toBe('page.html')
  })

  it('readFile 读取 Markdown 文件保留格式', async () => {
    const importer = useFileImporter()
    const md = '# 标题\n\n**粗体** *斜体* `代码`'
    const file = createMockFile(md, 'article.md', 'text/markdown')

    const result = await importer.readFile(file)

    expect(result!.text).toBe(md)
  })
})