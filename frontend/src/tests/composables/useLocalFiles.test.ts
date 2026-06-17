import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { useLocalFiles } from '@/components/widgets/create/useLocalFiles'

/**
 * 辅助函数：创建一个模拟 File 对象
 */
function createMockFile(name: string, size = 1024, lastModified = Date.now()): File {
  const blob = new Blob(['x'.repeat(size)], { type: 'text/plain' })
  return new File([blob], name, { lastModified })
}

describe('useLocalFiles', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('初始状态 stagedFiles 为空数组', () => {
    const { stagedFiles } = useLocalFiles()
    expect(stagedFiles.value).toEqual([])
  })

  it('stageFiles 添加文件并生成正确结构', () => {
    const { stagedFiles, stageFiles } = useLocalFiles()
    const file = createMockFile('test.txt')

    const added = stageFiles([file])

    expect(added).toHaveLength(1)
    expect(added[0]!.name).toBe('test.txt')
    expect(added[0]!.index).toBe(1)
    expect(added[0]!.id).toMatch(/^sf_\d+_\d+$/)
    expect(added[0]!.blobUrl).toMatch(/^blob:/)
    expect(added[0]!.file).toBe(file)
    expect(stagedFiles.value).toHaveLength(1)
  })

  it('stageFiles 自动去重：相同 name+size+lastModified 只保留一份', () => {
    const { stagedFiles, stageFiles } = useLocalFiles()
    const file = createMockFile('dup.txt', 100, 1234567890)

    stageFiles([file])
    stageFiles([file])

    expect(stagedFiles.value).toHaveLength(1)
  })

  it('stageFiles 可以添加多个不同文件，index 递增', () => {
    const { stagedFiles, stageFiles } = useLocalFiles()
    const file1 = createMockFile('a.txt', 100, 1)
    const file2 = createMockFile('b.txt', 200, 2)

    stageFiles([file1, file2])

    expect(stagedFiles.value).toHaveLength(2)
    expect(stagedFiles.value[0]!.index).toBe(1)
    expect(stagedFiles.value[1]!.index).toBe(2)
  })

  it('getByIndex 根据编号获取文件', () => {
    const { stageFiles, getByIndex } = useLocalFiles()
    const file = createMockFile('target.txt')
    stageFiles([file])

    const found = getByIndex(1)
    expect(found).toBeDefined()
    expect(found!.name).toBe('target.txt')

    expect(getByIndex(999)).toBeUndefined()
  })

  it('getReferencedFiles 解析正文中 [#N] 标记', () => {
    const { stageFiles, getReferencedFiles } = useLocalFiles()
    const f1 = createMockFile('img1.png')
    const f2 = createMockFile('doc.pdf')
    const f3 = createMockFile('img2.png')
    stageFiles([f1, f2, f3])

    const content = '这是第一张图 [#1] 和第三张图 [#3]，但不用第二张。'
    const refs = getReferencedFiles(content)

    expect(refs).toHaveLength(2)
    expect(refs.map((r) => r.name)).toEqual(['img1.png', 'img2.png'])
  })

  it('getReferencedFiles 内容中没有引用时返回空数组', () => {
    const { stageFiles, getReferencedFiles } = useLocalFiles()
    stageFiles([createMockFile('file.txt')])

    const refs = getReferencedFiles('没有任何引用的正文')
    expect(refs).toEqual([])
  })

  it('clearStaged 清空所有文件并释放 blob URL', () => {
    const revokeSpy = vi.spyOn(URL, 'revokeObjectURL')
    const { stagedFiles, stageFiles, clearStaged } = useLocalFiles()

    stageFiles([createMockFile('a.txt'), createMockFile('b.txt')])
    expect(stagedFiles.value).toHaveLength(2)

    clearStaged()

    expect(stagedFiles.value).toEqual([])
    expect(revokeSpy).toHaveBeenCalledTimes(2)
  })

  it('stageFiles 接收 FileList 也能正常工作', () => {
    const { stageFiles } = useLocalFiles()
    const file = createMockFile('from-list.txt')

    // FileList 是类数组对象，这里模拟一个类似 FileList 的结构
    const fakeFileList = [file] as unknown as FileList
    const added = stageFiles(fakeFileList)

    expect(added).toHaveLength(1)
    expect(added[0]!.name).toBe('from-list.txt')
  })

  it('getReferencedFiles 处理相邻多个引用', () => {
    const { stageFiles, getReferencedFiles } = useLocalFiles()
    const f1 = createMockFile('a.png')
    const f2 = createMockFile('b.png')
    const f3 = createMockFile('c.png')
    stageFiles([f1, f2, f3])

    const content = '图片 [#1][#2][#3]'
    const refs = getReferencedFiles(content)

    expect(refs).toHaveLength(3)
  })

  it('getReferencedFiles 处理超大编号', () => {
    const { stageFiles, getReferencedFiles } = useLocalFiles()
    const files = Array.from({ length: 100 }, (_, i) => createMockFile(`img${i + 1}.png`, 100, i))
    stageFiles(files)

    const content = '引用 [#1] 和 [#100]'
    const refs = getReferencedFiles(content)

    expect(refs).toHaveLength(2)
    expect(refs[0]!.index).toBe(1)
    expect(refs[1]!.index).toBe(100)
  })

  it('getReferencedFiles 忽略不完整的引用标记', () => {
    const { stageFiles, getReferencedFiles } = useLocalFiles()
    stageFiles([createMockFile('test.png')])

    // 缺少 ] 或 [ 的标记不应被匹配
    const content = '不完整标记 #1] 和 [#2 和 [abc]'
    const refs = getReferencedFiles(content)
    expect(refs).toEqual([])
  })

  it('getReferencedFiles 处理空内容', () => {
    const { stageFiles, getReferencedFiles } = useLocalFiles()
    stageFiles([createMockFile('test.png')])

    expect(getReferencedFiles('')).toEqual([])
  })

  it('getReferencedFiles 只返回已暂存文件中的引用', () => {
    const { stageFiles, getReferencedFiles } = useLocalFiles()
    const f1 = createMockFile('present.png')
    stageFiles([f1])

    // 引用 #999 不存在于暂存文件中
    const refs = getReferencedFiles('查看 [#1] 和 [#999]')
    expect(refs).toHaveLength(1)
    expect(refs[0]!.name).toBe('present.png')
  })
})
