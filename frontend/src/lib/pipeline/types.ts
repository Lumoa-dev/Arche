/**
 * types — 标准化流水线类型定义
 */
export type ParagraphType = 'text' | 'heading' | 'image' | 'video' | 'code' | 'table' | 'separator'

/** 解析器输出的原始段落 */
export interface RawParagraph {
  type: ParagraphType
  content: string
  heading?: string
}

/** 流水线最终输出的标准段落 */
export interface PipelineParagraph {
  type: ParagraphType
  content: string
  heading?: string
  media_url?: string
  caption?: string
}

/** 流水线最终输出 */
export interface PipelineResult {
  title: string
  subtitles: string[]
  introduction: string
  paragraphs: PipelineParagraph[]
  meta?: {
    tags?: string[]
    categories?: string[]
    date?: string
  }
}

/** 流水线阶段标识 */
export type PipelineStageName = 'frontmatter' | 'parse' | 'math' | 'image' | 'rearrange' | 'fill'

/** 阶段进度状态 */
export interface StageProgress {
  stage: PipelineStageName
  label: string
  status: 'pending' | 'running' | 'done' | 'error'
  progress: number
  message: string
  substeps?: { label: string; done: boolean }[]
}

/** 流水线整体进度 */
export interface PipelineProgress {
  stages: StageProgress[]
  currentStage: PipelineStageName | null
  overallProgress: number
  error?: string
}

/** 流水线选项 */
export interface PipelineOptions {
  source: 'import' | 'manual'
  /** 用户是否要求静默模式（隐藏弹窗） */
  silent?: boolean
  /** 进度回调 */
  onProgress?: (progress: PipelineProgress) => void
  /** 完成回调 */
  onComplete?: (result: PipelineResult) => void
  /** 错误回调 */
  onError?: (error: string) => void
}
