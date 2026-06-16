/**
 * MarkdownParser — 基于 marked.lexer() 的 MD 解析器
 *
 * 利用 marked 的词法分析器将 MD 文本解析为 Token AST，
 * 再映射为 RawParagraph[]（段落归一化）。
 * 支持 GFM / CommonMark / ``` / ~~~ / 表格 / 任务列表 / 链接引用等。
 */
import { marked } from 'marked'
import type { FileParser } from './FileParser'
import type { RawParagraph } from './types'

/** 段首中文关键词 → heading 标签 */
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

function detectKeywordHeading(text: string): string | null {
  const firstLine = text.split('\n')[0]?.trim() || ''
  for (const [kw, label] of Object.entries(KEYWORD_MAP)) {
    if (firstLine.startsWith(kw) && firstLine.length <= kw.length + 2) {
      return label
    }
  }
  return null
}

export class MarkdownParser implements FileParser {
  supportedExtensions(): string[] {
    return ['md', 'markdown']
  }

  parseRaw(text: string): RawParagraph[] {
    const result: RawParagraph[] = []
    const tokens = marked.lexer(text, { gfm: true })

    for (const token of tokens) {
      this.handleToken(token, result)
    }

    return result
  }

  private handleToken(token: marked.Token, result: RawParagraph[]): void {
    switch (token.type) {
      case 'heading': {
        const content = this.renderTokenContent(token)
        result.push({
          type: 'heading',
          content,
          heading: `H${token.depth}`
        })
        break
      }

      case 'paragraph': {
        const content = this.renderTokenContent(token)
        // 检查段落内容是否为纯图片
        const imgMatch = content.match(/^!\[([^\]]*)\]\(([^)]+)\)/)
        if (imgMatch) {
          result.push({
            type: 'image',
            content: imgMatch[1] || '',
            heading: undefined
          })
        } else {
          // 检测关键词
          const kw = detectKeywordHeading(content)
          const p: RawParagraph = { type: 'text', content }
          if (kw) {
            p.heading = kw
          }
          result.push(p)
        }
        break
      }

      case 'code': {
        result.push({
          type: 'code',
          content: token.text || ''
        })
        break
      }

      case 'table': {
        // 将 table token 结构渲染回类 MD 表格文本
        const tableText = this.renderTable(token)
        result.push({
          type: 'table',
          content: tableText
        })
        break
      }

      case 'hr': {
        result.push({
          type: 'separator',
          content: '---'
        })
        break
      }

      case 'blockquote': {
        const content = this.renderTokenContent(token)
        result.push({
          type: 'text',
          content: `> ${content}`
        })
        break
      }

      case 'list': {
        const content = this.renderList(token)
        result.push({
          type: 'text',
          content
        })
        break
      }

      case 'html': {
        result.push({
          type: 'text',
          content: token.text || ''
        })
        break
      }

      case 'space':
        // 空白 token 跳过
        break

      default: {
        // 兜底：尝试渲染文本
        const raw = (token as any).text
        if (raw) {
          result.push({
            type: 'text',
            content: String(raw)
          })
        }
        break
      }
    }
  }

  /** 渲染 token 的文本内容（递归处理子 token） */
  private renderTokenContent(token: marked.Token): string {
    // marked 的 heading / paragraph / blockquote 等都有 tokens 子数组
    const t = token as any
    if (t.tokens && Array.isArray(t.tokens)) {
      return t.tokens.map((sub: marked.Token) => this.renderInlineToken(sub)).join('')
    }
    // 兜底取 text 字段
    return t.text || ''
  }

  /** 渲染行内 token */
  private renderInlineToken(token: marked.Token): string {
    switch (token.type) {
      case 'text':
        return (token as any).text || ''
      case 'strong':
        return `**${this.renderTokenContent(token)}**`
      case 'em':
        return `*${this.renderTokenContent(token)}*`
      case 'del':
        return `~~${this.renderTokenContent(token)}~~`
      case 'code':
        return `\`${(token as any).text || ''}\``
      case 'link': {
        const t = token as any
        return `[${this.renderTokenContent(token)}](${t.href || ''})`
      }
      case 'image': {
        const t = token as any
        return `![${t.text || ''}](${t.href || ''})`
      }
      case 'br':
        return '\n'
      case 'html':
        return (token as any).text || ''
      default:
        return (token as any).text || ''
    }
  }

  /** 渲染列表 token 为纯文本 */
  private renderList(token: marked.Token): string {
    const t = token as any
    if (!t.items || !Array.isArray(t.items)) {
      return ''
    }
    const ordered = t.ordered || false
    return t.items
      .map((item: any, idx: number) => {
        const prefix = ordered ? `${idx + 1}. ` : '- '
        const text = this.renderTokenContent(item)
        // 检查是否为任务列表
        if (item.task === true) {
          const checked = item.checked ? 'x' : ' '
          return `${prefix}[${checked}] ${text}`
        }
        return `${prefix}${text}`
      })
      .join('\n')
  }

  /** 渲染 table token 为类 MD 表格文本 */
  private renderTable(token: marked.Token): string {
    const t = token as any
    if (!t.header || !t.rows) return ''

    const header = t.header.map((cell: any) => this.renderTokenContent(cell))
    const rows = t.rows.map((row: any[]) => row.map((cell: any) => this.renderTokenContent(cell)))
    const colCount = header.length
    const separator = `|${' --- |'.repeat(colCount)}`

    const headerLine = `| ${header.join(' | ')} |`
    const bodyLines = rows.map((row: string[]) => `| ${row.join(' | ')} |`)

    return [headerLine, separator, ...bodyLines].join('\n')
  }
}
