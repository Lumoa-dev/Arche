/**
 * useLocalFiles — 帖子素材本地暂存管理
 *
 * 核心逻辑：用户在点击"保存"之前，所有上传的素材只停留在浏览器内存中，
 * 不发送到服务器。保存时再由外层统一上传。
 */
import { onUnmounted, ref } from 'vue'

export interface StagedFile {
  /** 临时 ID（用于前端 key） */
  id: string
  /** 素材编号 #N */
  index: number
  /** 原始 File 对象 */
  file: File
  /** 本地 blob URL（用于预览） */
  blobUrl: string
  /** 文件名 */
  name: string
}

export function useLocalFiles() {
  let _nextId = 1
  let _nextIndex = 1
  const stagedFiles = ref<StagedFile[]>([])

  /** 文件特征 key：name + size + lastModified 近似视为同一文件 */
  function _fileKey(f: File): string {
    return `${f.name}_${f.size}_${f.lastModified}`
  }

  /** 添加文件到暂存区（自动去重） */
  function stageFiles(files: FileList | File[]): StagedFile[] {
    const existingKeys = new Set(stagedFiles.value.map((sf) => _fileKey(sf.file)))
    const added: StagedFile[] = []
    for (const file of Array.from(files)) {
      if (existingKeys.has(_fileKey(file))) continue
      existingKeys.add(_fileKey(file))
      const sf: StagedFile = {
        id: `sf_${Date.now()}_${_nextId++}`,
        index: _nextIndex++,
        file,
        blobUrl: URL.createObjectURL(file),
        name: file.name
      }
      added.push(sf)
    }
    stagedFiles.value = [...stagedFiles.value, ...added]
    return added
  }

  /** 根据编号获取暂存文件 */
  function getByIndex(index: number): StagedFile | undefined {
    return stagedFiles.value.find((f) => f.index === index)
  }

  /** 获取正文中所有被引用的暂存文件 */
  function getReferencedFiles(content: string): StagedFile[] {
    const refs = new Set<number>()
    const re = /\[#(\d+)\]/g
    let m: RegExpExecArray | null
    while ((m = re.exec(content)) !== null) {
      if (m[1]) refs.add(parseInt(m[1], 10))
    }
    return stagedFiles.value.filter((f) => refs.has(f.index))
  }

  /** 清空暂存区并释放 blob URL */
  function clearStaged() {
    stagedFiles.value.forEach((f) => URL.revokeObjectURL(f.blobUrl))
    stagedFiles.value = []
    _nextIndex = 1
  }

  /** 组件卸载时自动释放 blob URL，防止内存泄漏 */
  onUnmounted(() => {
    stagedFiles.value.forEach((f) => URL.revokeObjectURL(f.blobUrl))
  })

  return { stagedFiles, stageFiles, getByIndex, getReferencedFiles, clearStaged }
}
