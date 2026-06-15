/**
 * 预设渐变色集合。
 * 根据标题 + 标签的 hash 值分配一组渐变色。
 */
const GRADIENTS = [
  'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
  'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
  'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
  'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)',
  'linear-gradient(135deg, #fa709a 0%, #fee140 100%)',
  'linear-gradient(135deg, #a18cd1 0%, #fbc2eb 100%)',
  'linear-gradient(135deg, #fccb90 0%, #d57eeb 100%)',
  'linear-gradient(135deg, #e0c3fc 0%, #8ec5fc 100%)',
  'linear-gradient(135deg, #f5576c 0%, #ff6a6a 100%)',
  'linear-gradient(135deg, #667eea 0%, #4facfe 100%)',
  'linear-gradient(135deg, #30cfd0 0%, #330867 100%)',
  'linear-gradient(135deg, #a8edea 0%, #fed6e3 100%)'
]

function hashStr(str: string): number {
  let hash = 0
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i)
    hash = (hash << 5) - hash + char
    hash |= 0 // Convert to 32bit integer
  }
  return Math.abs(hash)
}

/**
 * 根据帖子信息获取封面渐变色。
 * 优先使用 cover_url，没有时根据标题+标签 hash 分配渐变色。
 */
export function getCoverGradient(post: { title?: string; tags?: string[] }): string {
  const seed = (post.title || '') + (post.tags?.join('') || '')
  const index = hashStr(seed) % GRADIENTS.length
  return GRADIENTS[index]!
}
