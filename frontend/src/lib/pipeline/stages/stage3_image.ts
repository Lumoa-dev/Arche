/**
 * stage3_image — 图片资源处理
 *
 * 扫描段落中的图片引用，执行：
 * 1. Base64 图片 → Canvas 解码 → WebP 无损转换 → OSS 上传 → 替换 URL
 * 2. 绝对 URL 图片 → 保持不动
 * 3. 相对路径图片 → 保持不动（浏览器端无法解析）
 *
 * 依赖 uploadOssFileApi 将图片上传到 OSS 存储。
 */
import { uploadOssFileApi } from '@/lib/services/api/oss'
import type { RawParagraph } from '../types'

/** 图片引用正则：![alt](url) */
const IMG_RE = /!\[([^\]]*)\]\(([^)]+)\)/g

/** Base64 图片前缀 */
const BASE64_PREFIX = 'data:image/'

/** 判断是否为 Base64 图片 */
function isBase64Image(url: string): boolean {
  return url.startsWith(BASE64_PREFIX)
}

/** 判断是否为绝对 URL */
function isAbsoluteUrl(url: string): boolean {
  return url.startsWith('http://') || url.startsWith('https://')
}

/**
 * 将 Base64 图片转为 WebP File
 *
 * 流程：
 *   1. 创建 Image 对象加载 Base64
 *   2. 绘制到 Canvas
 *   3. 导出为 WebP blob（无损质量 1.0）
 *   4. 包装为 File 对象
 */
function base64ToWebPFile(dataUrl: string, index: number): Promise<File> {
  return new Promise((resolve, reject) => {
    const img = new Image()
    img.onload = () => {
      const canvas = document.createElement('canvas')
      canvas.width = img.width
      canvas.height = img.height
      const ctx = canvas.getContext('2d')
      if (!ctx) {
        reject(new Error('Canvas 上下文获取失败'))
        return
      }
      ctx.drawImage(img, 0, 0)
      canvas.toBlob(
        (blob) => {
          if (blob) {
            resolve(new File([blob], `pipeline_img_${index}.webp`, { type: 'image/webp' }))
          } else {
            reject(new Error('WebP 转换失败'))
          }
        },
        'image/webp',
        1.0 // 无损
      )
    }
    img.onerror = () => reject(new Error('图片加载失败'))
    img.src = dataUrl
  })
}

/**
 * 处理单张图片引用
 *
 * @returns 替换后的 URL，或 null 表示无需替换
 */
async function processImageUrl(
  url: string,
  index: number,
  onSubstep?: (label: string, done: boolean) => void
): Promise<string | null> {
  // 绝对 URL → 保留不动
  if (isAbsoluteUrl(url)) {
    return null
  }

  // Base64 → 转 WebP → 上传 OSS
  if (isBase64Image(url)) {
    onSubstep?.(`正在转换图片 ${index + 1}...`, false)

    const webpFile = await base64ToWebPFile(url, index)

    onSubstep?.(`正在上传图片 ${index + 1}...`, false)

    try {
      const uploadResult = await uploadOssFileApi(webpFile, false)
      // 构造 OSS 文件访问 URL
      const ossUrl = `/api/oss/files/${uploadResult.id}`
      onSubstep?.(`图片 ${index + 1} 已上传`, true)
      return ossUrl
    } catch {
      // 上传失败，保留原样
      return null
    }
  }

  // 相对路径等无法处理的情况 → 保留不动
  return null
}

export interface Stage3ImageResult {
  paragraphs: RawParagraph[]
  imageCount: number
  uploadedCount: number
}

/**
 * Stage 3 主入口
 *
 * @param paragraphs - 前序阶段输出的段落列表
 * @param onProgress - 子步骤进度回调
 * @returns 图片 URL 已替换的段落列表
 */
export async function processImages(
  paragraphs: RawParagraph[],
  onProgress?: (message: string, substeps: { label: string; done: boolean }[]) => void
): Promise<Stage3ImageResult> {
  // 第一阶段：扫描所有段落，收集图片引用
  const imageRefs: { paragraphIndex: number; fullMatch: string; alt: string; url: string }[] = []

  for (let i = 0; i < paragraphs.length; i++) {
    const content = paragraphs[i]!.content
    let match: RegExpExecArray | null
    IMG_RE.lastIndex = 0
    while ((match = IMG_RE.exec(content)) !== null) {
      imageRefs.push({
        paragraphIndex: i,
        fullMatch: match[0],
        alt: match[1]!,
        url: match[2]!
      })
    }
  }

  if (imageRefs.length === 0) {
    return { paragraphs, imageCount: 0, uploadedCount: 0 }
  }

  const totalImages = imageRefs.length
  const substeps: { label: string; done: boolean }[] = [
    { label: `发现 ${totalImages} 张图片`, done: true }
  ]
  for (let i = 1; i <= totalImages; i++) {
    substeps.push({ label: `处理图片 ${i}/${totalImages}`, done: false })
  }
  onProgress?.('正在扫描图片引用...', substeps)

  let uploadedCount = 0
  let currentSubstepIndex = 1

  // 第二阶段：逐张处理图片
  for (const ref of imageRefs) {
    const newUrl = await processImageUrl(ref.url, currentSubstepIndex - 1, (label, done) => {
      substeps[currentSubstepIndex] = { label, done }
      onProgress?.(`正在处理第 ${currentSubstepIndex}/${totalImages} 张图片...`, [...substeps])
    })

    if (newUrl) {
      // 在段落内容中替换 URL
      const p = paragraphs[ref.paragraphIndex]!
      p.content = p.content.replace(ref.url, newUrl)
      uploadedCount++
    }

    substeps[currentSubstepIndex] = {
      label: newUrl ? `图片 ${currentSubstepIndex} 已处理` : `图片 ${currentSubstepIndex} 已跳过`,
      done: true
    }
    onProgress?.(`图片 ${currentSubstepIndex}/${totalImages} 处理完成`, [...substeps])
    currentSubstepIndex++
  }

  return { paragraphs, imageCount: totalImages, uploadedCount }
}
