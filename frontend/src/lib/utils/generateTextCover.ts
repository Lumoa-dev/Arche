/**
 * Canvas 文字封面生成工具。
 * 为无封面图的帖子自动生成一张"文字海报"风格的封面图片。
 * - 渐变色背景（复用 getCoverGradient）
 * - 正文片段（高斯模糊 3-5px 随机）
 * - 清晰标题 + 装饰分隔线 + 标签
 * - 纯前端 Canvas 渲染，零网络开销
 */

import { getCoverGradient } from './cover'
import type { BlogPost } from '@/components/logic/api'

/** canvas 输出尺寸 */
const W = 640
const H = 400

/** 简单 LRU 缓存，避免同一帖子重复生成 */
const cache = new Map<string, string>()

/** strip HTML tags */
function stripHtml(html: string): string {
  const el = document.createElement('div')
  el.innerHTML = html
  return el.textContent || ''
}

/** 从 post 中提取用于封面的文本片段 */
function extractText(post: BlogPost): string {
  // 优先级 1：引言 abstract
  if (post.introduction?.abstract?.trim()) return post.introduction.abstract.trim()

  // 优先级 2：段落数据第一段
  if (post.paragraphs?.length && post.paragraphs[0]?.content?.trim()) {
    return stripHtml(post.paragraphs[0].content).trim()
  }

  // 优先级 3：标题兜底
  return post.title?.trim() || ''
}

/** 在 3-5 之间随机取一个模糊像素值 */
function randomBlur(): number {
  return 3 + Math.random() * 2 // 3.0 ~ 4.999...
}

function parseGradient(style: string): CanvasGradient | null {
  // 从 "linear-gradient(135deg, #667eea 0%, #764ba2 100%)" 中提取色标
  const match = style.match(/linear-gradient\(.*?,\s*(.*?)\)\s*$/)
  if (!match) return null

  const stops: { pct: number; color: string }[] = []
  // 匹配 "(#xxx  xx%)" 或 "(#xxxxxx  xx%)"
  const re = /(#[\da-fA-F]+)\s+([\d.]+)%/g
  let m: RegExpExecArray | null
  while ((m = re.exec(match[1]!)) !== null) {
    stops.push({ color: m[1]!, pct: parseFloat(m[2]!) / 100 })
  }

  if (stops.length < 2) return null

  const canvas = document.createElement('canvas')
  const ctx = canvas.getContext('2d')!
  const grad = ctx.createLinearGradient(0, 0, W, H)
  for (const s of stops) grad.addColorStop(s.pct, s.color)
  return grad
}

/**
 * 为帖子生成文字封面图片。
 * @param post - 帖子数据
 * @param noCache - 强制不缓存（用于创建帖子时的预生成）
 * @returns data URL（image/jpeg, 0.85 质量）
 */
export function generateTextCover(post: BlogPost, noCache?: boolean): string {
  if (!noCache) {
    const cached = cache.get(post.id)
    if (cached) return cached
  }

  const canvas = document.createElement('canvas')
  canvas.width = W
  canvas.height = H
  const ctx = canvas.getContext('2d')!
  const text = extractText(post)

  // ── 1. 绘制背景渐变 ──
  const gradientCss = getCoverGradient(post)
  const grad = parseGradient(gradientCss)
  if (grad) {
    ctx.fillStyle = grad
  } else {
    ctx.fillStyle = '#667eea'
  }
  ctx.fillRect(0, 0, W, H)

  // ── 2. 装饰性底部渐变叠加层 ──
  const bottomGrad = ctx.createLinearGradient(0, H * 0.55, 0, H)
  bottomGrad.addColorStop(0, 'rgba(0,0,0,0)')
  bottomGrad.addColorStop(1, 'rgba(0,0,0,0.35)')
  ctx.fillStyle = bottomGrad
  ctx.fillRect(0, 0, W, H)

  // ── 3. 模糊正文片段 ──
  if (text) {
    ctx.save()
    ctx.filter = `blur(${randomBlur().toFixed(1)}px)`
    ctx.fillStyle = 'rgba(255,255,255,0.85)'
    ctx.font = 'bold 32px "Noto Sans SC", "PingFang SC", "Microsoft YaHei", sans-serif'
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'

    // 自动换行：每行最多 12 个字
    const maxCharsPerLine = 12
    const lines: string[] = []
    let remaining = text
    while (remaining.length > 0 && lines.length < 3) {
      if (remaining.length <= maxCharsPerLine) {
        lines.push(remaining)
        break
      }
      // 尽量在标点/空格处断开
      const slice = remaining.slice(0, maxCharsPerLine)
      const punctMatch = slice.match(/^.*?[，。、；：！？）」』"\s]/)
      const breakAt = punctMatch ? punctMatch[0].length : maxCharsPerLine
      lines.push(remaining.slice(0, breakAt))
      remaining = remaining.slice(breakAt).trim()
    }

    const lineHeight = 50
    const startY = H * 0.38 - ((lines.length - 1) * lineHeight) / 2
    for (let i = 0; i < lines.length; i++) {
      ctx.fillText(lines[i]!, W / 2, startY + i * lineHeight)
    }
    ctx.restore()
  }

  // ── 4. 装饰分隔线 ──
  const lineY = H * 0.72
  ctx.save()
  ctx.strokeStyle = 'rgba(255,255,255,0.25)'
  ctx.lineWidth = 1
  ctx.beginPath()
  ctx.moveTo(W * 0.25, lineY)
  ctx.lineTo(W * 0.75, lineY)
  ctx.stroke()
  ctx.restore()

  // ── 5. 标题（清晰，不模糊） ──
  ctx.save()
  ctx.fillStyle = '#fff'
  ctx.font = 'bold 22px "Noto Sans SC", "PingFang SC", "Microsoft YaHei", sans-serif'
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'

  const title = post.title || ''
  const displayTitle = title.length > 24 ? title.slice(0, 22) + '…' : title
  ctx.fillText(displayTitle, W / 2, H * 0.82)
  ctx.restore()

  // ── 6. 标签（右上角小标签） ──
  const tags = (post.tags || []).slice(0, 2)
  if (tags.length > 0) {
    ctx.save()
    ctx.font = '12px "Noto Sans SC", "PingFang SC", sans-serif'
    ctx.textAlign = 'right'
    ctx.textBaseline = 'top'

    let tx = W - 16
    const ty = 14
    for (let i = tags.length - 1; i >= 0; i--) {
      const label = tags[i]!
      const tw = ctx.measureText(label).width + 16
      // pill 背景
      ctx.fillStyle = 'rgba(0,0,0,0.25)'
      ctx.beginPath()
      ctx.roundRect(tx - tw + 4, ty - 4, tw, 22, 11)
      ctx.fill()
      // 文字
      ctx.fillStyle = 'rgba(255,255,255,0.8)'
      ctx.fillText(label, tx - 4, ty + 2)
      tx -= tw + 6
    }
    ctx.restore()
  }

  // ── 7. 左下角装饰（引号/标记） ──
  ctx.save()
  ctx.fillStyle = 'rgba(255,255,255,0.06)'
  ctx.font = '120px serif'
  ctx.textAlign = 'left'
  ctx.textBaseline = 'bottom'
  ctx.fillText('"', 14, H - 6)
  ctx.restore()

  const dataUrl = canvas.toDataURL('image/jpeg', 0.85)

  // 缓存最多 50 个，避免内存泄漏
  if (cache.size >= 50) {
    const firstKey = cache.keys().next().value
    if (firstKey) cache.delete(firstKey)
  }
  cache.set(post.id, dataUrl)

  return dataUrl
}
