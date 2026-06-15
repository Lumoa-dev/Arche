/**
 * useFileImporter — 文件导入 composable
 *
 * 读取 .md / .txt 文件 → 解析为结构化段落 → 填充到编辑器状态。
 * 供 EditorToolbar + editor.vue 使用。
 */
import { ref } from 'vue'
import { parseImportFile, type ImportResult } from '@/lib/utils/parseImportFile'
import type { ParagraphType, EditorParagraph } from './useParagraphEditor'

export function useFileImporter() {
  const importing = ref(false)
  const importError = ref<string | null>(null)

  let uidCounter = Date.now()

  function generateUid(): string {
    return `imp_${++uidCounter}`
  }

  /**
   * 读取并解析文件，返回结构化结果
   */
  async function readAndParse(file: File): Promise<ImportResult | null> {
    importing.value = true
    importError.value = null

    try {
      const text = await file.text()
      const result = parseImportFile(text, file.name)

      if (!result.title && result.paragraphs.length === 0) {
        importError.value = '文件内容为空或无法识别'
        return null
      }

      return result
    } catch (e) {
      importError.value = `文件读取失败: ${(e as Error).message}`
      return null
    } finally {
      importing.value = false
    }
  }

  /**
   * 将解析结果转换为 EditorParagraph 数组
   */
  function toEditorParagraphs(result: ImportResult): EditorParagraph[] {
    return result.paragraphs.map((p) => ({
      uid: generateUid(),
      type: p.type as ParagraphType,
      content: p.content,
      heading: p.heading,
      media_url: p.media_url,
      caption: p.caption
    }))
  }

  /**
   * 打开文件选择器并解析
   */
  function pickAndParse(): Promise<ImportResult | null> {
    return new Promise((resolve) => {
      const input = document.createElement('input')
      input.type = 'file'
      input.accept = '.md,.txt,.markdown'
      input.onchange = async () => {
        const file = input.files?.[0]
        if (!file) {
          resolve(null)
          return
        }
        const result = await readAndParse(file)
        resolve(result)
      }
      input.click()
    })
  }

  /**
   * 获取接受的文件类型标签
   */
  function acceptLabel(): string {
    return '.md, .txt, .markdown'
  }

  return {
    importing,
    importError,
    readAndParse,
    toEditorParagraphs,
    pickAndParse,
    acceptLabel
  }
}
