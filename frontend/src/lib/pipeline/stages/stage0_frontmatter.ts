/**
 * frontmatter — YAML/TOML Frontmatter 解析器
 *
 * 从 Markdown 文本中提取开头的元数据块，解析为结构化 meta。
 * 已知字段填入对应位置，未知字段的文本内容追加到引言。
 *
 * 支持的 Frontmatter 格式：
 * - YAML:  ---\nkey: value\n---\n
 * - TOML:  +++\nkey = "value"\n+++\n
 *
 * 注意：不使用完整 YAML 解析库，以正则处理常见格式。
 * 复杂嵌套 YAML（深层对象、锚点、合并标签等）作为纯文本保留。
 */

/** 已知的 meta 字段名（小写） */
const KNOWN_META_FIELDS = new Set([
  'title', 'tags', 'categories', 'category',
  'date', 'cover', 'cover_image', 'image',
  'description', 'summary', 'abstract', 'excerpt',
  'draft', 'published', 'status',
  'author', 'slug', 'permalink',
])

/** Frontmatter 解析结果 */
export interface FrontmatterResult {
  /** 去除 Frontmatter 后的纯正文 */
  body: string
  /** 提取的元数据 */
  meta: Record<string, unknown>
  /** 提取到的标题（仅当 Frontmatter 中有 title 字段） */
  title?: string
  /** 提取到的标签列表 */
  tags?: string[]
  /** 提取到的分类 */
  categories?: string[]
  /** 提取到的日期 */
  date?: string
  /** 提取到的封面 URL */
  coverUrl?: string
  /** 未知字段转为文本，作为引言内容 */
  introText: string
}

/** YAML frontmatter 定界符 */
const YAML_DELIM = /^---\s*$/
/** TOML frontmatter 定界符 */
const TOML_DELIM = /^\+\+\+\s*$/

/**
 * 解析 YAML 简单键值对行
 *
 * 支持：
 *   key: value
 *   key: "quoted value"
 *   key: [item1, item2, item3]
 *   key:
 *     - item1
 *     - item2
 */
function parseYamlLine(line: string): { key: string; value: string } | null {
  const match = line.match(/^([a-zA-Z_][a-zA-Z0-9_]*):\s*(.*)$/)
  if (!match) return null
  return {
    key: match[1]!.trim(),
    value: match[2]!.trim(),
  }
}

/** 解析 YAML 行内数组：[item1, item2, item3] */
function parseInlineArray(value: string): string[] | null {
  const match = value.match(/^\[([\s\S]*)\]$/)
  if (!match) return null
  return match[1]!.split(',').map((s) => s.trim().replace(/^["']|["']$/g, '')).filter(Boolean)
}

/** 解析 YAML 列表项：- item */
function isListItem(line: string): boolean {
  return /^\s*-\s+/.test(line)
}

function extractListItem(line: string): string {
  return line.replace(/^\s*-\s+/, '').trim().replace(/^["']|["']$/g, '')
}

/** 去除值的引号 */
function unquote(value: string): string {
  return value.replace(/^["']|["']$/g, '').trim()
}

/**
 * 从文本中提取 Frontmatter
 */
export function extractFrontmatter(text: string): FrontmatterResult {
  const lines = text.split('\n')
  const result: FrontmatterResult = {
    body: text,
    meta: {},
    introText: '',
  }

  // 检查第一行是否为定界符
  if (lines.length < 3) return result
  const firstLine = lines[0]?.trim() || ''

  const isYaml = YAML_DELIM.test(firstLine)
  const isToml = TOML_DELIM.test(firstLine)
  if (!isYaml && !isToml) return result

  // 查找结束定界符
  let endLine = -1
  for (let i = 1; i < lines.length; i++) {
    const testDelim = isYaml ? YAML_DELIM : TOML_DELIM
    if (testDelim.test(lines[i]!)) {
      endLine = i
      break
    }
  }

  if (endLine === -1) return result // 没有结束定界符，不当作 frontmatter

  // 解析定界符之间的内容
  const rawMeta: Record<string, string | string[]> = {}
  const rawLines = lines.slice(1, endLine)

  let currentKey: string | null = null
  const currentList: string[] = []

  for (const line of rawLines) {
    const trimmed = line.trim()

    // 列表项续接
    if (currentKey && isListItem(trimmed)) {
      currentList.push(extractListItem(trimmed))
      continue
    }

    // 上一个列表完成，存入
    if (currentKey && currentList.length > 0) {
      rawMeta[currentKey] = [...currentList]
      currentList.length = 0
      currentKey = null
    }

    const parsed = parseYamlLine(trimmed)
    if (!parsed) {
      // 非键值对行，可能是多行值的续行
      if (currentKey) {
        const existing = rawMeta[currentKey]
        if (typeof existing === 'string') {
          rawMeta[currentKey] = existing + '\n' + unquote(trimmed)
        }
      }
      continue
    }

    if (!parsed.value) {
      // 空值，可能是列表开始的标记
      currentKey = parsed.key
      continue
    }

    // 有值 → 检查是否为行内数组
    const arrayVal = parseInlineArray(parsed.value)
    if (arrayVal) {
      rawMeta[parsed.key.toLowerCase()] = arrayVal
    } else {
      rawMeta[parsed.key.toLowerCase()] = unquote(parsed.value)
    }
  }

  // 处理最后一个列表
  if (currentKey && currentList.length > 0) {
    rawMeta[currentKey] = [...currentList]
  }

  // 将 rawMeta 映射到结构化字段
  const unknownTextParts: string[] = []

  for (const [key, value] of Object.entries(rawMeta)) {
    result.meta[key] = value

    if (key === 'title' && typeof value === 'string') {
      result.title = value
    } else if (key === 'tags' || key === 'tag') {
      if (Array.isArray(value)) {
        result.tags = value as string[]
      } else if (typeof value === 'string') {
        result.tags = [value]
      }
    } else if (key === 'categories' || key === 'category') {
      if (Array.isArray(value)) {
        result.categories = value as string[]
      } else if (typeof value === 'string') {
        result.categories = [value]
      }
    } else if (key === 'date') {
      if (typeof value === 'string') {
        result.date = value
      }
    } else if (key === 'cover' || key === 'cover_image' || key === 'image') {
      if (typeof value === 'string') {
        result.coverUrl = value
      }
    } else if (
      key === 'description' || key === 'summary' ||
      key === 'abstract' || key === 'excerpt'
    ) {
      if (typeof value === 'string') {
        unknownTextParts.push(value)
      }
    } else if (KNOWN_META_FIELDS.has(key)) {
      // 已知字段但不在上述映射中 → 忽略
      // (draft, published, status, author, slug, permalink)
    } else {
      // 未知字段 → 进引言文本
      if (typeof value === 'string') {
        unknownTextParts.push(`${key}: ${value}`)
      } else if (Array.isArray(value)) {
        unknownTextParts.push(`${key}: ${(value as string[]).join(', ')}`)
      }
    }
  }

  // 未知字段拼为引言文本
  if (unknownTextParts.length > 0) {
    result.introText = unknownTextParts.join('\n')
  }

  // 正文 = 结束定界符之后的内容
  result.body = lines.slice(endLine + 1).join('\n').trim()

  return result
}
