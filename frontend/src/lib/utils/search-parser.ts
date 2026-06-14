/**
 * 搜索语法解析器 —— 解析类 GitHub 风格的搜索语法。
 *
 * 支持的语法：
 *   key:value   → 精确筛选（如 type:post, status:active, id:xxx）
 *   is:keyword  → 限定词筛选（如 is:open）
 *   纯文本      → 模糊搜索文本
 *
 * @example
 * parseSearchQuery('type:post status:active 如何优化')
 * // → { text: '如何优化', filters: [{ key: 'type', value: 'post' }, { key: 'status', value: 'active' }] }
 */

export interface SearchFilter {
  key: string
  value: string
  raw: string
}

export interface ParsedQuery {
  text: string
  filters: SearchFilter[]
}

// 支持的 key:value 语法键列表
const FILTER_KEYS = new Set([
  'type',
  'id',
  'sid',
  'status',
  'author',
  'tag',
  'user',
  'username',
  'is'
])

/**
 * 解析搜索输入字符串为结构化查询。
 *
 * 解析规则：
 * 1. 扫描 `key:value` 模式的片段（key 必须在 FILTER_KEYS 中）
 * 2. `is:value` 也按 filter 解析，key 为 'is'
 * 3. 剩余未匹配的片段合并为 text
 */
export function parseSearchQuery(input: string): ParsedQuery {
  const trimmed = input.trim()
  if (!trimmed) {
    return { text: '', filters: [] }
  }

  // 按空格分词，但保留引号内的内容
  const tokens = tokenize(trimmed)
  const filters: SearchFilter[] = []
  const textParts: string[] = []

  for (const token of tokens) {
    const filter = tryParseFilter(token)
    if (filter) {
      filters.push(filter)
    } else {
      textParts.push(token)
    }
  }

  return {
    text: textParts.join(' ').trim(),
    filters
  }
}

/**
 * 分词：支持用引号括起来的词组。
 * 例如：type:post "hello world" → ['type:post', 'hello world']
 */
function tokenize(input: string): string[] {
  const tokens: string[] = []
  const re = /[^\s"']+|"([^"]*)"|'([^']*)'/g
  let match: RegExpExecArray | null

  while ((match = re.exec(input)) !== null) {
    // 引号内的内容去掉引号
    tokens.push(match[1] ?? match[2] ?? match[0])
  }

  return tokens
}

/**
 * 尝试将一个 token 解析为 SearchFilter。
 * 格式必须是 `key:value` 且 key 在 FILTER_KEYS 中。
 */
function tryParseFilter(token: string): SearchFilter | null {
  const colonIndex = token.indexOf(':')
  if (colonIndex <= 0) {
    return null
  }

  const key = token.slice(0, colonIndex).toLowerCase()
  const value = token.slice(colonIndex + 1)

  if (!FILTER_KEYS.has(key)) {
    return null
  }

  return { key, value, raw: token }
}

/**
 * 从解析结果中提取指定 key 的 filter 值。
 */
export function getFilterValue(parsed: ParsedQuery, key: string): string | undefined {
  return parsed.filters.find((f) => f.key === key)?.value
}

/**
 * 判断解析结果是否包含 SID 匹配（id: 或 sid: 前缀）。
 */
export function hasIdFilter(parsed: ParsedQuery): boolean {
  return parsed.filters.some((f) => f.key === 'id' || f.key === 'sid')
}

/**
 * 获取纯 SID 搜索文本（移除所有 key:value 后的剩余字符串）。
 */
export function getSearchText(input: string): string {
  return parseSearchQuery(input).text
}
