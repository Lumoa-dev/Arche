/**
 * useFileImporter — 文件导入 composable（简化版）
 *
 * 读取 .md / .txt 文件内容，直接返回文本字符串。
 * 不进行任何解析，由 TipTap 编辑器自行处理渲染。
 */
import { ref } from 'vue'

export interface FileImportResult {
  text: string
  fileName: string
}

export function useFileImporter() {
  const importing = ref(false)
  const importError = ref<string | null>(null)

  /**
   * 读取文件内容
   */
  async function readFile(file: File): Promise<FileImportResult | null> {
    importing.value = true
    importError.value = null

    try {
      const text = await file.text()
      if (!text.trim()) {
        importError.value = '文件内容为空'
        return null
      }
      return { text, fileName: file.name }
    } catch (e) {
      importError.value = `文件读取失败: ${(e as Error).message}`
      return null
    } finally {
      importing.value = false
    }
  }

  /**
   * 打开文件选择器并读取
   */
  function pickAndRead(): Promise<FileImportResult | null> {
    return new Promise((resolve) => {
      const input = document.createElement('input')
      input.type = 'file'
      input.accept = '.md,.txt,.markdown,.html'
      input.onchange = async () => {
        const file = input.files?.[0]
        if (!file) {
          resolve(null)
          return
        }
        const result = await readFile(file)
        resolve(result)
      }
      input.click()
    })
  }

  return {
    importing,
    importError,
    readFile,
    pickAndRead
  }
}
