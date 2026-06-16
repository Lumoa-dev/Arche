/**
 * FileParser — 文件解析器接口
 *
 * 所有文件格式解析器必须实现此接口。
 * 新增格式（DOCX/PDF/HTML 等）只需实现此接口即可接入流水线。
 */
import type { RawParagraph } from './types'

export interface FileParser {
  /** 支持的文件扩展名列表（不含点号） */
  supportedExtensions(): string[]

  /** 解析文本为原始段落列表 */
  parseRaw(text: string): RawParagraph[]
}

/** 按扩展名查找对应的解析器 */
export function findParser(parsers: FileParser[], fileName: string): FileParser | undefined {
  const ext = fileName.toLowerCase().split('.').pop() || ''
  return parsers.find((p) => p.supportedExtensions().includes(ext))
}

/** 获取支持的文件扩展名标签 */
export function supportedExtensionsLabel(parsers: FileParser[]): string {
  const exts = new Set<string>()
  for (const p of parsers) {
    for (const ext of p.supportedExtensions()) {
      exts.add(`.${ext}`)
    }
  }
  return Array.from(exts).join(', ')
}
