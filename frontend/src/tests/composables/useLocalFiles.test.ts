import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { useLocalFiles } from '@/components/logic/useLocalFiles'

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
})
