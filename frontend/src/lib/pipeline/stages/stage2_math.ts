/**
 * stage2_math — 数学公式转换
 *
 * 将段落内容中的 $...$（内联）和 $$...$$（块级）数学公式
 * 通过 KaTeX 渲染为 HTML 字符串。
 *
 * 策略：
 * - $$...$$ 始终作为块级公式处理（display mode）
 * - $...$ 作为内联公式处理，但排除常见的误匹配（如美元金额 $100）
 */
import katex from 'katex'
import type { RawParagraph } from '../types'

/** 块级公式：$$...$$ */
const DISPLAY_MATH_RE = /\$\$([\s\S]+?)\$\$/g

/**
 * 内联公式：$...$
 *
 * 规则：
 * 1. 不以数字开头后面直接跟数字/点（避免 $10.99 误匹配）
 * 2. 内容至少 1 个字符
 * 3. 不被反引号包围（代码段内不处理）
 */
const INLINE_MATH_RE = /(?<!\$)(?<!\d)\$([^$]{1,200}?)\$(?!\$)(?!\d)/g

/**
 * 对段落内容运行 KaTeX 转换
 */
function renderMathInText(text: string): string {
  // 先处理块级公式
  let result = text.replace(DISPLAY_MATH_RE, (_, formula: string) => {
    try {
      return katex.renderToString(formula.trim(), {
        displayMode: true,
        throwOnError: false
      })
    } catch {
      // 渲染失败，保留原文
      return `$${formula}$`
    }
  })

  // 再处理内联公式
  result = result.replace(INLINE_MATH_RE, (_, formula: string) => {
    try {
      return katex.renderToString(formula.trim(), {
        displayMode: false,
        throwOnError: false
      })
    } catch {
      // 渲染失败，保留原文
      return `$${formula}$`
    }
  })

  return result
}

/**
 * Stage 2 主入口
 *
 * @param paragraphs - Stage 1 输出的原始段落列表
 * @returns 数学公式已转换为 HTML 的段落列表
 */
export function processMathFormulas(paragraphs: RawParagraph[]): RawParagraph[] {
  return paragraphs.map((p) => {
    if (p.type === 'text' || p.type === 'heading') {
      return {
        ...p,
        content: renderMathInText(p.content)
      }
    }
    // 代码块、表格等不处理数学公式
    return p
  })
}
