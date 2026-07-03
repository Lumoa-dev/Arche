import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useFileImporter } from '@/components/widgets/create/useFileImporter'

describe('useFileImporter', () => {
  it('初始状态：importing 为 false，importError 为 null', () => {
    const importer = useFileImporter()

    expect(importer.importing.value).toBe(false)
    expect(importer.importError.value).toBeNull()
  })

  it('readFile 成功读取文件内容', async () => {
    const importer = useFileImporter()

    const file = new File(['Hello, World!'], 'test.txt', { type: 'text/plain' })
    const result = await importer.readFile(file)

    expect(result).not.toBeNull()
    expect(result!.text).toBe('Hello, World!')
    expect(result!.fileName).toBe('test.txt')
    expect(importer.importing.value).toBe(false)
    expect(importer.importError.value).toBeNull()
  })

  it('readFile 读取空内容时返回 null 并设置错误', async () => {
    const importer = useFileImporter()

    const file = new File([''], 'empty.txt', { type: 'text/plain' })
    const result = await importer.readFile(file)

    expect(result).toBeNull()
    expect(importer.importError.value).toBe('文件内容为空')
  })

  it('readFile 读取空白内容时返回 null', async () => {
    const importer = useFileImporter()

    const file = new File(['   '], 'whitespace.txt', { type: 'text/plain' })
    const result = await importer.readFile(file)

    expect(result).toBeNull()
    expect(importer.importError.value).toBe('文件内容为空')
  })

  it('readFile 读取大文件不报错', async () => {
    const importer = useFileImporter()

    const largeContent = 'x'.repeat(100000)
    const file = new File([largeContent], 'large.txt', { type: 'text/plain' })
    const result = await importer.readFile(file)

    expect(result).not.toBeNull()
    expect(result!.text).toHaveLength(100000)
    expect(importer.importing.value).toBe(false)
  })

  it('readFile 读取 .md 文件', async () => {
    const importer = useFileImporter()

    const mdContent = '# Title\n\nThis is a markdown file.'
    const file = new File([mdContent], 'post.md', { type: 'text/markdown' })
    const result = await importer.readFile(file)

    expect(result).not.toBeNull()
    expect(result!.text).toBe(mdContent)
    expect(result!.fileName).toBe('post.md')
  })

  it('readFile 读取 .html 文件', async () => {
    const importer = useFileImporter()

    const html = '<p>Hello</p>'
    const file = new File([html], 'page.html', { type: 'text/html' })
    const result = await importer.readFile(file)

    expect(result).not.toBeNull()
    expect(result!.text).toBe(html)
  })

  it('importing 在读取过程中为 true', async () => {
    const importer = useFileImporter()

    // 创建一个延迟读取的 file 对象
    const file = new File(['test'], 'test.txt', { type: 'text/plain' })

    // 开始读取，但等待完成
    const promise = importer.readFile(file)
    expect(importer.importing.value).toBe(true)

    await promise
    expect(importer.importing.value).toBe(false)
  })
})