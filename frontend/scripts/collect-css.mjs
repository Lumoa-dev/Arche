/**
 * CSS 收集脚本
 *
 * 扫描 frontend/src/ 下所有 .vue 和 .css 文件，提取全部 CSS 内容，
 * 输出聚合文件供分析和管理。
 *
 * 用法: node scripts/collect-css.mjs
 * 输出:
 *   - dist/css-collected/collected.css   — 全部 CSS 聚合（含来源注释）
 *   - dist/css-collected/report.json     — 结构化元数据
 */

import { readFileSync, writeFileSync, existsSync, mkdirSync } from 'fs'
import { join, relative, resolve } from 'path'
import { fileURLToPath } from 'url'
import { globSync } from 'glob'

const __dirname = fileURLToPath(new URL('.', import.meta.url))
const ROOT = resolve(__dirname, '..')
const SRC = join(ROOT, 'src')

const OUTPUT_DIR = join(ROOT, 'dist', 'css-collected')
const OUTPUT_CSS = join(OUTPUT_DIR, 'collected.css')
const OUTPUT_REPORT = join(OUTPUT_DIR, 'report.json')

// 确保输出目录存在
if (!existsSync(OUTPUT_DIR)) {
  mkdirSync(OUTPUT_DIR, { recursive: true })
}

// ===== 提取 CSS 工具 =====

/** 从 .vue 文件内容中提取 <style> 块 */
function extractVueStyles(content, filePath) {
  const blocks = []

  // 匹配 <style scoped>...</style> 或 <style>...</style>
  const styleRegex = /<style\b([^>]*)>([\s\S]*?)<\/style>/g
  let match

  while ((match = styleRegex.exec(content)) !== null) {
    const attrs = match[1] || ''
    const body = match[2].trim()
    const isScoped = attrs.includes('scoped')
    const lang = (attrs.match(/lang=["'](\w+)["']/) || [])[1] || 'css'

    if (body && lang === 'css') {
      blocks.push({
        scoped: isScoped,
        body,
        raw: match[0],
      })
    }
  }

  return blocks
}

/** 从 .css 文件内容中提取全部内容 */
function extractCssContent(content) {
  return content.trim()
}

// ===== 文件扫描 =====

const cssFiles = globSync('src/**/*.css', { cwd: ROOT })
const vueFiles = globSync('src/**/*.vue', { cwd: ROOT })

const allBlocks = []

//  处理 .css 文件
for (const file of cssFiles) {
  const absPath = join(ROOT, file)
  const content = readFileSync(absPath, 'utf-8')
  const css = extractCssContent(content)
  if (!css) continue

  allBlocks.push({
    source: file,
    type: 'css',
    scoped: false,
    lines: css.split('\n').length,
    body: css,
  })
}

//  处理 .vue 文件
for (const file of vueFiles) {
  const absPath = join(ROOT, file)
  const content = readFileSync(absPath, 'utf-8')
  const blocks = extractVueStyles(content, file)

  for (const block of blocks) {
    allBlocks.push({
      source: file,
      type: 'vue',
      scoped: block.scoped,
      lines: block.body.split('\n').length,
      body: block.body,
    })
  }
}

// ===== 生成聚合 CSS =====

const header = `/* =============================================================
   CSS 聚合文件 — 自动生成，请勿手动修改
   生成时间: ${new Date().toISOString()}
   来源文件: ${allBlocks.length} 个样式块
   来自 ${cssFiles.length} 个 .css 文件 + ${vueFiles.length} 个 .vue 文件
   ============================================================= */

`

const cssParts = allBlocks.map((block) => {
  const scopedTag = block.scoped ? ' [scoped]' : ''
  return `/* ─── ${block.source}${scopedTag} ─── */\n${block.body}`
})

writeFileSync(OUTPUT_CSS, header + cssParts.join('\n\n'), 'utf-8')

// ===== 生成报告 =====

// 统计按来源目录分组
const groups = {}
for (const block of allBlocks) {
  const parts = block.source.replace(/\\/g, '/').split('/')
  const dir =
    parts[0] === 'src'
      ? parts.slice(0, 3).join('/')
      : parts[0]

  if (!groups[dir]) {
    groups[dir] = { files: new Set(), blocks: 0, lines: 0, scopedLines: 0 }
  }
  groups[dir].files.add(block.source)
  groups[dir].blocks++
  groups[dir].lines += block.lines
  if (block.scoped) groups[dir].scopedLines += block.lines
}

// 转换为序列化格式
const reportGroups = {}
for (const [dir, info] of Object.entries(groups)) {
  reportGroups[dir] = {
    files: [...info.files].sort(),
    blocks: info.blocks,
    lines: info.lines,
    scopedLines: info.scopedLines,
  }
}

const totalLines = allBlocks.reduce((s, b) => s + b.lines, 0)
const scopedLines = allBlocks.filter((b) => b.scoped).reduce((s, b) => s + b.lines, 0)

const report = {
  generatedAt: new Date().toISOString(),
  summary: {
    cssFiles: cssFiles.length,
    vueFiles: vueFiles.length,
    totalBlocks: allBlocks.length,
    totalLines,
    scopedLines,
    globalLines: totalLines - scopedLines,
  },
  groups: reportGroups,
  top20: allBlocks
    .sort((a, b) => b.lines - a.lines)
    .slice(0, 20)
    .map((b) => ({
      source: b.source,
      scoped: b.scoped,
      lines: b.lines,
    })),
  blocks: allBlocks.map((b) => ({
    source: b.source,
    type: b.type,
    scoped: b.scoped,
    lines: b.lines,
  })),
}

writeFileSync(OUTPUT_REPORT, JSON.stringify(report, null, 2), 'utf-8')

// ===== 打印摘要 =====

console.log('')
console.log('  CSS 收集完成!')
console.log('  ───────────────────────────────────')
console.log(`  来源:       ${cssFiles.length} 个 .css + ${vueFiles.length} 个 .vue = ${allBlocks.length} 个样式块`)
console.log(`  总行数:     ${totalLines} 行`)
console.log(`    其中 scope: ${scopedLines} 行`)
console.log(`    其中全局:   ${totalLines - scopedLines} 行`)
console.log('')
console.log('  输出:')
console.log(`  ${OUTPUT_CSS}`)
console.log(`  ${OUTPUT_REPORT}`)
console.log('')

// 按目录输出占比
console.log('  按目录分布:')
console.log('  ───────────────────────────────────')
const sorted = Object.entries(reportGroups).sort((a, b) => b[1].lines - a[1].lines)
for (const [dir, info] of sorted) {
  const pct = ((info.lines / totalLines) * 100).toFixed(1)
  console.log(`  ${dir.padEnd(30)} ${String(info.lines).padStart(6)} 行 (${pct}%)  ${info.blocks} 块`)
}
console.log('')
