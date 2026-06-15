/**
 * Canvas 文字封面生成工具。
 * 为无封面图的帖子自动生成一张"文字海报"风格的封面图片。
 * - 正文片段（高斯模糊）+ 随机裁切布局
 * - 清晰标题（占小比例）+ 引言/正文填充
 * - 文字色彩调制 + 模糊装饰
 * - 纯前端 Canvas 渲染
 */

import { getCoverGradient } from './cover'
import { htmlToText } from './string'
import type { BlogPost } from '@/components/logic/api'

const W = 640
const H = 400

const cache = new Map<string, string>()

function stripHtml(html: string): string {
  return htmlToText(html)
}

/** 从 post 提取用于封面渲染的文本素材 */
function extractTexts(post: BlogPost): {
  title: string
  bodyLines: string[]
} {
  const title = post.title?.trim() || ''
  const bodyChunks: string[] = []

  // 引言
  if (post.introduction?.trim()) {
    bodyChunks.push(stripHtml(post.introduction).trim())
  }

  // 段落正文（取前 3 段）
  if (post.paragraphs?.length) {
    for (let i = 0; i < Math.min(3, post.paragraphs.length); i++) {
      const text = stripHtml(post.paragraphs[i]?.content || '').trim()
      if (text) bodyChunks.push(text)
    }
  }

  // 将正文打散成行（每行 10-16 字随机裁切）
  const full = bodyChunks.join('　')
  const lines: string[] = []
  let pos = 0
  while (pos < full.length && lines.length < 12) {
    const len = 10 + Math.floor(Math.random() * 7) // 10~16 字随机
    lines.push(full.slice(pos, pos + len))
    pos += len
  }

  return { title, bodyLines: lines }
}

function parseGradient(style: string): CanvasGradient | null {
  const match = style.match(/linear-gradient\(.*?,\s*(.*?)\)\s*$/)
  if (!match) return null
  const stops: { pct: number; color: string }[] = []
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

export function generateTextCover(post: BlogPost, noCache?: boolean): string {
  if (!noCache) {
    const cached = cache.get(post.id)
    if (cached) return cached
  }

  const canvas = document.createElement('canvas')
  canvas.width = W
  canvas.height = H
  const ctx = canvas.getContext('2d')!

  // 随机种子偏移
  const seed = post.title?.length ?? 0

  const { title, bodyLines } = extractTexts(post)

  // ── 1. 背景渐变 ──
  const gradientCss = getCoverGradient(post)
  const grad = parseGradient(gradientCss)
  ctx.fillStyle = grad ?? '#667eea'
  ctx.fillRect(0, 0, W, H)

  // ── 2. 装饰叠加层 ──
  const overlayGrad = ctx.createLinearGradient(0, 0, 0, H)
  overlayGrad.addColorStop(0, 'rgba(0,0,0,0)')
  overlayGrad.addColorStop(1, 'rgba(0,0,0,0.3)')
  ctx.fillStyle = overlayGrad
  ctx.fillRect(0, 0, W, H)

  // ── 3. 模糊正文层（随机裁切布局） ──
  //    制造"看不清又看得清"的模糊背景文字
  if (bodyLines.length > 0) {
    ctx.save()
    ctx.textBaseline = 'middle'

    const baseSize = 26 + (seed % 8)
    const blurAmount = 3 + (seed % 3)

    ctx.filter = `blur(${blurAmount}px)`

    // 色彩调制：根据文字长度偏移 HSL
    const hueShift = (seed * 37) % 360
    ctx.fillStyle = `hsla(${hueShift}, 60%, 70%, 0.5)`

    // 随机布局：每行随机位置、旋转
    const usedPositions: { x: number; y: number }[] = []
    const lineCount = Math.min(bodyLines.length, 8)

    for (let i = 0; i < lineCount; i++) {
      const line = bodyLines[i]!
      ctx.font = `bold ${baseSize + (i % 3) * 4}px "Noto Sans SC","PingFang SC","Microsoft YaHei",sans-serif`

      // 随机位置（避免过于重叠）
      let x: number,
        y: number,
        attempts = 0
      do {
        x = 20 + Math.random() * (W - 80)
        y = 20 + Math.random() * (H - 60)
        attempts++
      } while (
        attempts < 20 &&
        usedPositions.some((p) => Math.abs(p.x - x) < 60 && Math.abs(p.y - y) < 40)
      )
      usedPositions.push({ x, y })

      // 随机旋转（-15° ~ +15°）
      const angle = ((Math.random() - 0.5) * 30 * Math.PI) / 180

      ctx.save()
      ctx.translate(x, y)
      ctx.rotate(angle)
      ctx.textAlign = 'left'

      // 随机色彩偏移
      const lineHue = (hueShift + i * 47) % 360
      ctx.fillStyle = `hsla(${lineHue}, 50%, 75%, 0.45)`

      ctx.fillText(line, 0, 0)
      ctx.restore()
    }

    ctx.restore()
  }

  // ── 4. 装饰性几何元素 ──
  ctx.save()
  for (let i = 0; i < 3; i++) {
    const cx = 40 + Math.random() * (W - 80)
    const cy = 30 + Math.random() * (H - 100)
    const r = 8 + Math.random() * 20
    ctx.beginPath()
    ctx.arc(cx, cy, r, 0, Math.PI * 2)
    ctx.fillStyle = `rgba(255,255,255,${0.03 + Math.random() * 0.05})`
    ctx.fill()
  }
  ctx.restore()

  // ── 5. 标题（清晰，小比例 — 底部区域） ──
  if (title) {
    ctx.save()

    // 标题底色 pill
    const displayTitle = title.length > 28 ? title.slice(0, 26) + '…' : title
    ctx.font = 'bold 20px "Noto Sans SC","PingFang SC","Microsoft YaHei",sans-serif'
    const tw = ctx.measureText(displayTitle).width
    const pillW = tw + 32
    const pillH = 38
    const pillX = (W - pillW) / 2
    const pillY = H - 56

    ctx.fillStyle = 'rgba(0,0,0,0.25)'
    ctx.beginPath()
    ctx.roundRect(pillX, pillY, pillW, pillH, 19)
    ctx.fill()

    // 标题文字
    ctx.fillStyle = '#fff'
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    ctx.font = 'bold 20px "Noto Sans SC","PingFang SC","Microsoft YaHei",sans-serif'
    ctx.fillText(displayTitle, W / 2, pillY + pillH / 2)

    ctx.restore()
  }

  // ── 6. 标签（右上角） ──
  const tags = (post.tags || []).slice(0, 2)
  if (tags.length > 0) {
    ctx.save()
    ctx.font = '11px "Noto Sans SC","PingFang SC",sans-serif'
    ctx.textAlign = 'right'
    ctx.textBaseline = 'top'

    let tx = W - 14
    const ty = 12
    for (let i = tags.length - 1; i >= 0; i--) {
      const label = tags[i]!
      const tw = ctx.measureText(label).width + 14
      ctx.fillStyle = 'rgba(0,0,0,0.2)'
      ctx.beginPath()
      ctx.roundRect(tx - tw + 3, ty - 3, tw, 20, 10)
      ctx.fill()
      ctx.fillStyle = 'rgba(255,255,255,0.75)'
      ctx.fillText(label, tx - 3, ty + 2)
      tx -= tw + 4
    }
    ctx.restore()
  }

  // ── 7. 左下角装饰引号 ──
  ctx.save()
  ctx.fillStyle = 'rgba(255,255,255,0.05)'
  ctx.font = '100px serif'
  ctx.textAlign = 'left'
  ctx.textBaseline = 'bottom'
  ctx.fillText('"', 12, H - 8)
  ctx.restore()

  const dataUrl = canvas.toDataURL('image/jpeg', 0.85)

  if (cache.size >= 50) {
    const firstKey = cache.keys().next().value
    if (firstKey) cache.delete(firstKey)
  }
  cache.set(post.id, dataUrl)

  return dataUrl
}
