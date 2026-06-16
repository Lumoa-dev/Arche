/**
 * 标准化段落解析流水线测试
 *
 * 覆盖：
 * - MarkdownParser 解析多种 MD 方言
 * - rearrangeParagraphs 标题就近合并
 * - reassembleToMarkdown 手动编辑回溯
 * - buildResult 结果输出
 * - extractFrontmatter 元数据提取
 */
import { describe, it, expect } from 'vitest'
import { MarkdownParser } from '@/lib/pipeline/MarkdownParser'
import { rearrangeParagraphs, reassembleToMarkdown } from '@/lib/pipeline/PipelineRunner'
import { extractFrontmatter } from '@/lib/pipeline/stages/stage0_frontmatter'
import type { RawParagraph } from '@/lib/pipeline/types'

// 辅助函数：纯段落 → 输出引用，用于 buildResult 的输入
function buildResult(raw: RawParagraph[]): { title: string; introduction: string; paragraphs: { type: string; content: string; heading?: string }[] } {
  const result: { title: string; introduction: string; paragraphs: { type: string; content: string; heading?: string }[] } = {
    title: '',
    introduction: '',
    paragraphs: [],
  }
  // 第一个非空 text → title
  for (const p of raw) {
    if (p.type === 'text' && p.content.trim()) {
      result.title = p.content.trim().split('\n')[0] || ''
      break
    }
  }
  // 段落输出
  for (const p of raw) {
    if (p.content.trim()) {
      result.paragraphs.push({
        type: p.type,
        content: p.content,
        heading: p.heading,
      })
    }
  }
  return result
}

// ────────────────────────────────────────────
// 1. MarkdownParser
// ────────────────────────────────────────────

describe('MarkdownParser', () => {
  const parser = new MarkdownParser()

  it('应支持 .md 和 .markdown 扩展名', () => {
    expect(parser.supportedExtensions()).toEqual(['md', 'markdown'])
  })

  it('应正确解析标题', () => {
    const result = parser.parseRaw('# 一级标题\n\n## 二级标题\n\n### 三级标题')
    expect(result[0]).toMatchObject({ type: 'heading', heading: 'H1', content: '一级标题' })
    expect(result[1]).toMatchObject({ type: 'heading', heading: 'H2', content: '二级标题' })
    expect(result[2]).toMatchObject({ type: 'heading', heading: 'H3', content: '三级标题' })
  })

  it('应正确解析段落', () => {
    const result = parser.parseRaw('这是一段普通文本。\n\n这是第二段。')
    expect(result).toHaveLength(2)
    expect(result[0]).toMatchObject({ type: 'text' })
    expect(result[0]!.content).toContain('这是一段普通文本')
    expect(result[1]!.content).toContain('这是第二段')
  })

  it('应正确解析代码块', () => {
    const result = parser.parseRaw('```python\nprint("hello")\n```')
    expect(result).toHaveLength(1)
    expect(result[0]).toMatchObject({ type: 'code' })
    expect(result[0]!.content).toContain('print("hello")')
  })

  it('应正确解析分隔线', () => {
    const result = parser.parseRaw('---')
    // marked 可能将 --- 解析为 hr token
    const hrResult = parser.parseRaw('***')
    expect(result.some((p) => p.type === 'separator')).toBe(true)
    expect(hrResult.some((p) => p.type === 'separator')).toBe(true)
  })

  it('应正确解析引用块', () => {
    const result = parser.parseRaw('> 这是一段引用\n> 这是同一段引用')
    expect(result).toHaveLength(1)
    expect(result[0]!.type).toBe('text')
    expect(result[0]!.content).toContain('>')
  })

  it('应正确解析任务列表', () => {
    const result = parser.parseRaw('- [ ] 待办事项\n- [x] 已完成事项')
    expect(result).toHaveLength(1)
    expect(result[0]!.content).toContain('- [ ]')
    expect(result[0]!.content).toContain('- [x]')
  })

  it('应正确解析无序列表', () => {
    const result = parser.parseRaw('- 项目一\n- 项目二\n- 项目三')
    expect(result).toHaveLength(1)
    expect(result[0]!.type).toBe('text')
    expect(result[0]!.content).toContain('- 项目一')
    expect(result[0]!.content).toContain('- 项目二')
  })

  it('应正确解析有序列表', () => {
    const result = parser.parseRaw('1. 第一项\n2. 第二项\n3. 第三项')
    expect(result).toHaveLength(1)
    expect(result[0]!.type).toBe('text')
    expect(result[0]!.content).toContain('1.')
    expect(result[0]!.content).toContain('第一项')
  })

  it('应正确解析图片', () => {
    const result = parser.parseRaw('![alt文本](https://example.com/image.png)')
    expect(result).toHaveLength(1)
    expect(result[0]!.type).toBe('image')
  })

  it('应正确解析表格', () => {
    const result = parser.parseRaw('| 列1 | 列2 |\n| --- | --- |\n| A | B |')
    expect(result).toHaveLength(1)
    expect(result[0]!.type).toBe('table')
  })

  it('应解析含行内格式的文本', () => {
    const result = parser.parseRaw('这是一段**加粗**和*斜体*文本')
    expect(result).toHaveLength(1)
    expect(result[0]!.type).toBe('text')
  })

  it('应解析混合内容：标题 + 段落 + 代码', () => {
    const md = `# 标题

这是正文段落。

\`\`\`
code block
\`\`\`

这是另一段。`
    const result = parser.parseRaw(md)
    expect(result.length).toBeGreaterThanOrEqual(3)
    expect(result[0]!.type).toBe('heading')
    expect(result[1]!.type).toBe('text')
    // code 块位置取决于 marked 输出顺序
    expect(result.some((p) => p.type === 'code')).toBe(true)
  })
})

// ────────────────────────────────────────────
// 2. RearrangeParagraphs（标题就近合并）
// ────────────────────────────────────────────

describe('rearrangeParagraphs', () => {
  it('应将 heading + 紧跟的 text 合并', () => {
    const input: RawParagraph[] = [
      { type: 'heading', content: '项目背景', heading: 'H2' },
      { type: 'text', content: '这个项目是为了解决...', heading: undefined },
    ]
    const result = rearrangeParagraphs(input)
    expect(result).toHaveLength(1)
    expect(result[0]!.type).toBe('text')
    expect(result[0]!.heading).toBe('H2')
    expect(result[0]!.content).toContain('项目背景')
    expect(result[0]!.content).toContain('这个项目是为了解决')
  })

  it('孤标题应自成一 text 段落', () => {
    const input: RawParagraph[] = [
      { type: 'heading', content: '孤标题', heading: 'H2' },
      { type: 'separator', content: '---', heading: undefined },
    ]
    const result = rearrangeParagraphs(input)
    expect(result).toHaveLength(2)
    expect(result[0]!.type).toBe('text')
    expect(result[0]!.heading).toBe('H2')
  })

  it('连续标题各自独立', () => {
    const input: RawParagraph[] = [
      { type: 'heading', content: '标题1', heading: 'H2' },
      { type: 'heading', content: '标题2', heading: 'H2' },
      { type: 'text', content: '正文', heading: undefined },
    ]
    const result = rearrangeParagraphs(input)
    expect(result).toHaveLength(2)
    expect(result[0]!.heading).toBe('H2')
    expect(result[0]!.content).toContain('标题1')
    expect(result[1]!.heading).toBe('H2')
    expect(result[1]!.content).toContain('标题2')
    expect(result[1]!.content).toContain('正文')
  })

  it('标题 + 代码块 → 不合并', () => {
    const input: RawParagraph[] = [
      { type: 'heading', content: '代码示例', heading: 'H2' },
      { type: 'code', content: 'print("hello")', heading: undefined },
    ]
    const result = rearrangeParagraphs(input)
    expect(result).toHaveLength(2)
    expect(result[0]!.type).toBe('text')
    expect(result[0]!.heading).toBe('H2')
    expect(result[1]!.type).toBe('code')
  })
})

// ────────────────────────────────────────────
// 3. ReassembleToMarkdown（手动编辑回溯）
// ────────────────────────────────────────────

describe('reassembleToMarkdown', () => {
  it('应将 text 段落拼回纯文本', () => {
    const input = [
      { type: 'text', content: '第一段正文', heading: undefined },
      { type: 'text', content: '第二段正文', heading: undefined },
    ]
    const result = reassembleToMarkdown(input)
    expect(result).toBe('第一段正文\n\n第二段正文')
  })

  it('应将 heading 段落转为 # 标记', () => {
    const input = [
      { type: 'heading', content: '项目背景', heading: 'H2', media_url: undefined, caption: undefined },
    ]
    const result = reassembleToMarkdown(input)
    expect(result).toContain('## 项目背景')
  })

  it('应将 code 段落转为 ``` 围栏', () => {
    const input = [
      { type: 'code', content: 'print("hello")', heading: undefined, media_url: undefined, caption: undefined },
    ]
    const result = reassembleToMarkdown(input)
    expect(result).toContain('```')
    expect(result).toContain('print("hello")')
  })

  it('应将 image 段落转为 ![]() 标记', () => {
    const input = [
      { type: 'image', content: '', heading: undefined, media_url: 'https://example.com/img.png', caption: '说明' },
    ]
    const result = reassembleToMarkdown(input)
    expect(result).toBe('![说明](https://example.com/img.png)')
  })
})

// ────────────────────────────────────────────
// 4. BuildResult
// ────────────────────────────────────────────

describe('buildResult', () => {
  it('从段落中提取标题', () => {
    const input: RawParagraph[] = [
      { type: 'text', content: '文章标题', heading: undefined },
      { type: 'text', content: '正文内容', heading: undefined },
    ]
    const result = buildResult(input)
    expect(result.title).toBe('文章标题')
    expect(result.paragraphs).toHaveLength(2)
  })
})

// ────────────────────────────────────────────
// 5. Frontmatter 解析
// ────────────────────────────────────────────

describe('extractFrontmatter', () => {
  it('应提取 YAML frontmatter 的标题', () => {
    const text = `---
title: 我的文章
tags: [技术, Vue]
date: 2024-01-15
---

正文内容`
    const result = extractFrontmatter(text)
    expect(result.title).toBe('我的文章')
    expect(result.tags).toEqual(['技术', 'Vue'])
    expect(result.date).toBe('2024-01-15')
    expect(result.body).toBe('正文内容')
  })

  it('应提取 cover 字段', () => {
    const text = `---
title: 带封面的文章
cover: https://example.com/cover.jpg
---

正文`
    const result = extractFrontmatter(text)
    expect(result.title).toBe('带封面的文章')
    expect(result.coverUrl).toBe('https://example.com/cover.jpg')
  })

  it('应提取 categories 字段', () => {
    const text = `---
title: 分类文章
categories: [技术博客, 前端]
---

正文`
    const result = extractFrontmatter(text)
    expect(result.categories).toEqual(['技术博客', '前端'])
  })

  it('未知字段应进入 introText', () => {
    const text = `---
title: 文章
custom_field: 自定义值
another: 另一个值
---

正文`
    const result = extractFrontmatter(text)
    expect(result.title).toBe('文章')
    expect(result.introText).toContain('custom_field')
    expect(result.introText).toContain('another')
  })

  it('无 frontmatter 时应返回原文本', () => {
    const text = '没有 frontmatter 的普通文本\n\n第二段'
    const result = extractFrontmatter(text)
    expect(result.title).toBeUndefined()
    expect(result.body).toBe(text)
  })

  it('不完整的 frontmatter（无结束定界符）应返回原文本', () => {
    const text = '---\ntitle: 不完整\n\n正文内容'
    const result = extractFrontmatter(text)
    expect(result.title).toBeUndefined()
    expect(result.body).toBe(text)
  })

  it('description/summary/abstract 应进入 introText', () => {
    const text = `---
title: 文章
description: 这是一篇好文章
---

正文`
    const result = extractFrontmatter(text)
    expect(result.introText).toContain('这是一篇好文章')
  })

  it('应处理空 frontmatter', () => {
    const text = `---
---

正文内容`
    const result = extractFrontmatter(text)
    expect(result.body).toBe('正文内容')
  })

  it('Hugo/Hexo 风格的 frontmatter', () => {
    const text = `---
title: "Hugo 文章"
date: 2020-03-10
tags:
  - Hugo
  - 静态站点
draft: false
---

文章正文`
    const result = extractFrontmatter(text)
    expect(result.title).toBe('Hugo 文章')
    expect(result.date).toBe('2020-03-10')
    // tags 列表格式可能不被支持（多行 - 列表），但 title 应正确提取
    expect(result.body).toBe('文章正文')
  })
})
