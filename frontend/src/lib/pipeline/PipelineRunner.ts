/**
 * PipelineRunner — 标准化流水线执行器
 *
 * 统一处理文件导入和手动编辑两种场景。
 * 流程：
 *   import:  原始文本 → Stage1 解析 → Stage2 数学公式 → Stage3 图片 → Stage4 重整 → Stage5 填充
 *   manual:  EditorParagraph[] → 回溯为 MD → Stage1 解析 → Stage2/3/4/5
 */
import { MarkdownParser } from './MarkdownParser'
import { findParser } from './FileParser'
import type { FileParser } from './FileParser'
import type {
  PipelineResult,
  PipelineParagraph,
  RawParagraph,
  PipelineOptions,
  PipelineProgress,
  StageProgress,
  PipelineStageName,
} from './types'
import { processMathFormulas } from './stages/stage2_math'
import { processImages } from './stages/stage3_image'

/** 流水线默认阶段定义 */
const STAGE_DEFS: { name: PipelineStageName; label: string }[] = [
  { name: 'parse', label: '正在解析源文本...' },
  { name: 'math', label: '正在转换数学公式...' },
  { name: 'image', label: '正在处理图片资源...' },
  { name: 'rearrange', label: '正在重整段落结构...' },
  { name: 'fill', label: '正在填充到编辑器...' }
]

function buildInitialProgress(): PipelineProgress {
  return {
    stages: STAGE_DEFS.map((def, idx) => ({
      stage: def.name,
      label: def.label,
      status: idx === 0 ? ('pending' as const) : ('pending' as const),
      progress: 0,
      message: ''
    })),
    currentStage: null,
    overallProgress: 0
  }
}

function updateStage(
  progress: PipelineProgress,
  stage: PipelineStageName,
  updates: Partial<StageProgress>
): void {
  const s = progress.stages.find((s) => s.stage === stage)
  if (s) {
    Object.assign(s, updates)
  }
}

/**
 * 将 EditorParagraph[] 回溯为 Markdown 文本
 *
 * 手动编辑的段落结构被用户打乱过（段落膨胀），
 * 回溯到 MD 文本再走一遍流水线，可以重新归一化。
 */
export function reassembleToMarkdown(
  paragraphs: {
    type: string
    content: string
    heading?: string
    media_url?: string
    caption?: string
  }[]
): string {
  return paragraphs
    .map((p) => {
      switch (p.type) {
        case 'heading': {
          const level = p.heading?.match(/H(\d)/)?.[1] || '2'
          const marker = '#'.repeat(parseInt(level))
          return `${marker} ${p.content}`
        }
        case 'code':
          return '```\n' + p.content + '\n```'
        case 'image':
          return `![${p.caption || ''}](${p.media_url || ''})`
        case 'separator':
          return '---'
        case 'table':
          return p.content
        default:
          // text 及兜底
          return p.content
      }
    })
    .join('\n\n')
}

/**
 * Stage 4: 段落重整（标题就近合并 + 清理）
 *
 * 核心规则：
 * 1. heading 段落 → 如果下一个段落是 text → 合并到 text 的 heading 字段
 * 2. heading 段落 → 如果下一个不是 text（code/separator/image/结尾）→ 自己独立成 text 段落
 * 3. 孤立的 heading 段落（无后续正文）→ 转为 text，heading 字段保留
 */
function rearrangeParagraphs(raw: RawParagraph[]): RawParagraph[] {
  const result: RawParagraph[] = []

  for (let i = 0; i < raw.length; i++) {
    const p = raw[i]!

    if (p.type !== 'heading') {
      result.push(p)
      continue
    }

    // 看下一个段落
    const next = raw[i + 1]

    if (next && next.type === 'text') {
      // heading + text → 合并，heading 字段记标题，content 保留原始标记
      const headingLabel = p.heading
      result.push({
        type: 'text',
        content: `${p.content}\n\n${next.content}`,
        heading: headingLabel
      })
      i++ // 跳过已合并的 text
    } else {
      // heading 后面不是 text → 自己当一段
      result.push({
        type: 'text',
        content: p.content,
        heading: p.heading
      })
    }
  }

  return result
}

/**
 * Stage 5: 填充输出结构
 *
 * 从标准化的 RawParagraph[] 构建 PipelineResult。
 * 提取标题（第一个段落或第一行非空文本）和引言。
 */
function buildResult(raw: RawParagraph[]): PipelineResult {
  const result: PipelineResult = {
    title: '',
    subtitles: [],
    introduction: '',
    paragraphs: []
  }

  // 第一个非空 text/heading 段落 → 作为标题
  let titleIdx = -1
  for (let i = 0; i < raw.length; i++) {
    const p = raw[i]!
    if (p.type === 'text' && p.content.trim()) {
      titleIdx = i
      const firstLine = p.content.trim().split('\n')[0] || ''
      result.title = firstLine
      break
    }
  }

  // 标题后的第一个 text 段落较短时作为引言
  if (titleIdx >= 0) {
    for (let j = titleIdx + 1; j < raw.length; j++) {
      const p = raw[j]!
      if (p.type === 'text' && p.content.trim()) {
        if (p.content.trim().length < 100 && !p.heading) {
          result.introduction = p.content.trim()
          // 标记已消费，跳过
          raw[j] = { type: 'text', content: '' }
        }
        break
      }
    }
  }

  // 剩余段落 → 输出（rearrangeParagraphs 已处理 heading 合并，不需要再 mergeSections）
  for (const p of raw) {
    if (p.content.trim()) {
      result.paragraphs.push({
        type: p.type,
        content: p.content,
        heading: p.heading
      })
    }
  }

  return result
}

/** 将 heading 段落与紧随的 text 合并，保持当前系统兼容 */
function mergeSections(paragraphs: RawParagraph[]): RawParagraph[] {
  const merged: RawParagraph[] = []
  for (let i = 0; i < paragraphs.length; i++) {
    const p = paragraphs[i]!
    if (p.type !== 'heading') {
      merged.push(p)
      continue
    }

    const bodyParts: string[] = []
    bodyParts.push(p.content)

    let j = i + 1
    while (j < paragraphs.length) {
      const next = paragraphs[j]!
      if (next.type === 'heading') break
      if (next.type === 'separator') {
        j++
        break
      }
      if (next.type === 'image') break
      bodyParts.push('')
      bodyParts.push(next.content)
      j++
    }

    merged.push({
      type: 'text',
      content: bodyParts.join('\n'),
      heading: p.heading
    })
    i = j - 1
  }
  return merged
}

/**
 * 执行完整流水线
 *
 * @param input - 输入文本（import 场景）或段落数组（manual 场景）
 * @param fileName - 文件名（用来选解析器）
 * @param options - 流水线选项
 */
export async function runPipeline(
  input:
    | string
    | { type: string; content: string; heading?: string; media_url?: string; caption?: string }[],
  fileName: string,
  options: PipelineOptions
): Promise<PipelineResult> {
  const progress = buildInitialProgress()
  const notify = (p: PipelineProgress) => options.onProgress?.(p)

  try {
    // ── Stage 1: 解析 ──
    progress.currentStage = 'parse'
    updateStage(progress, 'parse', {
      status: 'running',
      progress: 0,
      message: '正在初始化解析器...'
    })
    notify(progress)

    let text: string
    const source = options.source

    if (source === 'manual' && Array.isArray(input)) {
      updateStage(progress, 'parse', {
        progress: 30,
        message: '正在将编辑器内容回溯为 Markdown...'
      })
      notify(progress)
      text = reassembleToMarkdown(input)
    } else if (typeof input === 'string') {
      text = input
    } else {
      throw new Error('输入格式不匹配：manual 场景需要段落数组，import 场景需要文本')
    }

    updateStage(progress, 'parse', { progress: 60, message: '正在解析 Markdown 语法结构...' })
    notify(progress)

    const parser = findParser([new MarkdownParser()], fileName) as FileParser
    if (!parser) {
      throw new Error(`不支持的文件格式: ${fileName}`)
    }

    const rawParagraphs = parser.parseRaw(text)
    updateStage(progress, 'parse', {
      status: 'done',
      progress: 100,
      message: `解析完成，共 ${rawParagraphs.length} 个段落`
    })
    notify(progress)

    // ── Stage 2: 数学公式 ──
    progress.currentStage = 'math'
    updateStage(progress, 'math', { status: 'running', progress: 10, message: '正在扫描数学公式...' })
    notify(progress)

    const mathProcessed = processMathFormulas(rawParagraphs)
    updateStage(progress, 'math', { status: 'done', progress: 100, message: '数学公式转换完成' })
    notify(progress)

    // ── Stage 3: 图片处理 ──
    progress.currentStage = 'image'
    updateStage(progress, 'image', { status: 'running', progress: 0, message: '正在扫描图片引用...' })
    notify(progress)

    const {
      paragraphs: imageProcessed,
      imageCount,
      uploadedCount,
    } = await processImages(mathProcessed, (message, substeps) => {
      updateStage(progress, 'image', { progress: 30, message, substeps })
      notify(progress)
    })

    if (imageCount > 0) {
      const skipCount = imageCount - uploadedCount
      let msg = `共处理 ${imageCount} 张图片`
      if (uploadedCount > 0) msg += `，已上传 ${uploadedCount} 张`
      if (skipCount > 0) msg += `，${skipCount} 张跳过`
      updateStage(progress, 'image', { status: 'done', progress: 100, message: msg })
    } else {
      updateStage(progress, 'image', { status: 'done', progress: 100, message: '未发现图片引用' })
    }
    notify(progress)

    // ── Stage 4: 段落重整 ──
    progress.currentStage = 'rearrange'
    updateStage(progress, 'rearrange', { status: 'running', progress: 0, message: '正在合并标题与正文...' })
    notify(progress)

    const rearranged = rearrangeParagraphs(imageProcessed)
    updateStage(progress, 'rearrange', { progress: 60, message: '正在清理空段落...' })
    notify(progress)

    updateStage(progress, 'rearrange', { status: 'done', progress: 100, message: '段落重整完成' })
    notify(progress)

    // ── Stage 5: 填充输出 ──
    progress.currentStage = 'fill'
    updateStage(progress, 'fill', { status: 'running', progress: 0, message: '正在构建最终结果...' })
    notify(progress)

    const result = buildResult(rearranged)
    updateStage(progress, 'fill', { status: 'done', progress: 100, message: '填充完成' })
    notify(progress)

    // 更新整体进度
    progress.currentStage = null
    progress.overallProgress = 100
    notify(progress)

    options.onComplete?.(result)
    return result
  } catch (e) {
    const msg = (e as Error).message || '流水线执行失败'
    progress.error = msg
    notify(progress)
    options.onError?.(msg)
    throw e
  }
}

/** 获取流水线阶段列表（供 UI 组件渲染进度条） */
export function getStageLabels(): { name: PipelineStageName; label: string }[] {
  return STAGE_DEFS
}
