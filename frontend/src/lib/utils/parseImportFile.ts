/**
 * parseImportFile — 导入文件解析器
 *
 * 将 .md / .txt 文件内容解析为编辑器可用的结构化段落数据。
 * - 硬段落扫描：空行分隔
 * - 词语检测：特殊关键词标记段落
 * - Markdown：标题 # / 副标题 >（仅行首有效）/ 分隔线 --- / 图片 ![]()
 */
import type { ParagraphType } from '@/components/logic/useParagraphEditor'

export interface ImportParagraph {
  type: ParagraphType
  content: string
  heading?: string
  media_url?: string
  caption?: string
}

export interface ImportResult {
  title: string
  subtitles: string[]
  introduction: string
  paragraphs: ImportParagraph[]
}

/** 硬段落扫描关键词 → 映射为段落标题 */
const KEYWORD_MAP: Record<string, string> = {
  摘要: '摘要',
  简介: '简介',
  概述: '概述',
  前言: '前言',
  背景: '背景',
  总结: '总结',
  结论: '结论',
  附录: '附录',
  参考: '参考'
}

/** 检查行是否为关键词标题 */
function detectKeywordHeading(line: string): string | null {
  const trimmed = line.trim()
  for (const [kw, label] of Object.entries(KEYWORD_MAP)) {
    if (trimmed.startsWith(kw) && trimmed.length <= kw.length + 2) {
      return label
    }
  }
  return null
}

/** 检测行内是否包含年份标记 */
function detectYearMarker(line: string): boolean {
  return /(^|\s)(\d{4})年(\s|$|[，。、；：])/.test(line.trim())
}

/** 解析 .md 格式文本 */
function parseMarkdown(text: string): ImportResult {
  const lines = text.split('\n')
  const result: ImportResult = {
    title: '',
    subtitles: [],
    introduction: '',
    paragraphs: []
  }

  let i = 0
  let inCodeBlock = false

  // ── 第 1 行如果是 # 标题 → 取为标题 ──
  const firstHeading = lines[0]?.match(/^#\s+(.+)/)
  if (firstHeading) {
    result.title = firstHeading[1]!.trim()
    i = 1
  } else {
    // 否则取第一行非空作为标题
    while (i < lines.length && !lines[i]!.trim()) i++
    if (i < lines.length) {
      result.title = lines[i]!.trim()
      i++
    }
  }

  // ── 逐行扫描 ──
  let currentParagraph = ''
  let isIntroduction = true // 引言标记：正文前的连续段落

  function flushParagraph() {
    if (!currentParagraph.trim()) return

    const trimmed = currentParagraph.trim()

    // 检测分隔线
    if (/^-{3,}\s*$/.test(trimmed)) {
      result.paragraphs.push({ type: 'separator', content: '---' })
      currentParagraph = ''
      return
    }

    // 检测图片
    const imgMatch = trimmed.match(/^!\[([^\]]*)\]\(([^)]+)\)/)
    if (imgMatch) {
      const cap = imgMatch[1] || undefined
      result.paragraphs.push({
        type: 'image',
        content: '',
        ...(cap ? { caption: cap } : {}),
        media_url: imgMatch[2]!
      })
      currentParagraph = ''
      return
    }

    // 引言模式：正文开始前的段落
    if (isIntroduction && result.paragraphs.length === 0) {
      result.introduction = (result.introduction ? result.introduction + '\n' : '') + trimmed
      currentParagraph = ''
      return
    }

    // 关键词检测 → heading 类型
    const kw = detectKeywordHeading(trimmed)
    if (kw) {
      result.paragraphs.push({ type: 'heading', content: trimmed, heading: kw })
      currentParagraph = ''
      return
    }

    // 年份标记 → 加 heading 标签
    if (detectYearMarker(trimmed)) {
      result.paragraphs.push({ type: 'heading', content: trimmed, heading: trimmed.slice(0, 10) })
      currentParagraph = ''
      return
    }

    // 普通段落
    result.paragraphs.push({ type: 'text', content: trimmed })
    currentParagraph = ''
  }

  while (i < lines.length) {
    const line = lines[i]!

    // 代码块开关
    if (line.trim().startsWith('```')) {
      if (!inCodeBlock) {
        flushParagraph()
        inCodeBlock = true
        i++
        continue
      } else {
        // 代码块结束，将收集的代码作为一个 code 段落
        inCodeBlock = false
        if (currentParagraph.trim()) {
          result.paragraphs.push({ type: 'code', content: currentParagraph.trim() })
          currentParagraph = ''
        }
        i++
        continue
      }
    }

    if (inCodeBlock) {
      currentParagraph += line + '\n'
      i++
      continue
    }

    // 空行 → 段落分割
    if (!line.trim()) {
      flushParagraph()
      i++
      continue
    }

    // # 标题 → heading 段落（不写入 subtitles：subtitles 是文章副标题，不是章节标题）
    const hMatch = line.match(/^(#{2,4})\s+(.+)/)
    if (hMatch) {
      flushParagraph()
      const level = hMatch[1]!.length
      const text = hMatch[2]!.trim()
      result.paragraphs.push({ type: 'heading', content: text, heading: `H${level}` })
      i++
      continue
    }

    // > 引用 → 引言或副标题（仅行首有效）
    const bqMatch = line.match(/^>\s*(.+)/)
    if (bqMatch) {
      const quoteText = bqMatch[1]!.trim()

      // 如果已有正文内容，当作 quote 段落
      if (result.paragraphs.length > 0 || result.introduction) {
        result.paragraphs.push({ type: 'text', content: `> ${quoteText}` })
      } else {
        // 正文前的引用 → 当作 introduction
        result.introduction = (result.introduction ? result.introduction + '\n' : '') + quoteText
      }
      i++
      continue
    }

    // 分隔线 ---
    if (/^-{3,}\s*$/.test(line)) {
      flushParagraph()
      result.paragraphs.push({ type: 'separator', content: '---' })
      i++
      continue
    }

    // 普通行 → 追加到当前段落
    currentParagraph += line + '\n'
    isIntroduction = false
    i++
  }

  flushParagraph()

  // ── 后处理：将 heading + 紧接的正文合并为整段 ──
  //    避免"标题和正文拆成独立卡片"导致联动问题
  result.paragraphs = mergeSections(result.paragraphs)

  return result
}

/**
 * 将 heading 段落与紧随其后的非 heading 段落合并为单个 text 段落。
 * 分隔线/图片等保留不合并。
 */
function mergeSections(paragraphs: ImportParagraph[]): ImportParagraph[] {
  const merged: ImportParagraph[] = []

  for (let i = 0; i < paragraphs.length; i++) {
    const p = paragraphs[i]!

    // 非 heading → 直接保留
    if (p.type !== 'heading') {
      merged.push(p)
      continue
    }

    // heading → 收集后续段落（直到下一个 heading 或 separator 或 image）
    const bodyParts: string[] = []

    // 提取 heading 标记
    const level = p.heading?.match(/H(\d)/)?.[1] || '2'
    const headingMarker = '#'.repeat(parseInt(level))
    bodyParts.push(`${headingMarker} ${p.content}`)

    // 向后收集连续的 text / code 段落
    let j = i + 1
    while (j < paragraphs.length) {
      const next = paragraphs[j]!
      if (next.type === 'heading') break // 下一个 heading → 结束
      if (next.type === 'separator') {
        // 分隔线 → 保留但不吞并
        j++
        break
      }
      if (next.type === 'image') break // 图片 → 不吞并
      // text / code → 合并进当前段
      bodyParts.push('')
      bodyParts.push(next.content)
      j++
    }

    // 合并为一个 text 段落
    merged.push({
      type: 'text',
      content: bodyParts.join('\n')
    })

    i = j - 1 // 跳到已合并的最后一项
  }

  return merged
}

/** 解析 .txt 纯文本 */
function parsePlainText(text: string): ImportResult {
  const result: ImportResult = {
    title: '',
    subtitles: [],
    introduction: '',
    paragraphs: []
  }

  const blocks = text
    .split(/\n\s*\n/)
    .map((b) => b.trim())
    .filter(Boolean)

  if (blocks.length === 0) return result

  // 第一块作为标题
  result.title = blocks[0]!
  let startIdx = 1

  // 第二块如果较短（< 100 字）作为引言
  if (blocks.length > 1 && blocks[1]!.length < 100) {
    result.introduction = blocks[1]!
    startIdx = 2
  }

  for (let j = startIdx; j < blocks.length; j++) {
    const block = blocks[j]!

    // 分隔线
    if (/^-{3,}$/.test(block)) {
      result.paragraphs.push({ type: 'separator', content: '---' })
      continue
    }

    // 关键词检测
    const kw = detectKeywordHeading(block)
    if (kw) {
      result.paragraphs.push({ type: 'heading', content: block, heading: kw })
      continue
    }

    // 年份标记
    if (detectYearMarker(block)) {
      result.paragraphs.push({ type: 'heading', content: block, heading: block.slice(0, 10) })
      continue
    }

    // 普通段落
    result.paragraphs.push({ type: 'text', content: block })
  }

  return result
}

/**
 * 解析导入文件内容
 * @param text 文件内容
 * @param fileName 文件名（用于判定格式）
 */
export function parseImportFile(text: string, fileName: string): ImportResult {
  const ext = fileName.toLowerCase().split('.').pop()

  if (ext === 'md' || ext === 'markdown') {
    return parseMarkdown(text)
  }

  // .txt 及兜底
  return parsePlainText(text)
}
