/**
 * 图片格式转换脚本
 * 将 JPG 图片转换为 WebP 格式
 */
import { dirname, join } from 'path'
import { fileURLToPath } from 'url'

import sharp from 'sharp'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

const imagesDir = join(__dirname, '..', 'src', 'assets', 'images')

const images = [
  { name: 'welcome-hero', width: 1920, height: 1080 },
  { name: 'login-bg', width: 800, height: 600 },
  { name: 'agreement-header', width: 1920, height: 600 },
  { name: 'empty-state', width: 400, height: 400 },
]

async function convertImages() {
  for (const img of images) {
    const jpgPath = join(imagesDir, `${img.name}.jpg`)
    const webpPath = join(imagesDir, `${img.name}.webp`)
    const mobileWebpPath = join(imagesDir, `${img.name}-mobile.webp`)
    const mobileJpgPath = join(imagesDir, `${img.name}-mobile.jpg`)

    try {
      // 生成 WebP 格式（质量 80%）
      await sharp(jpgPath)
        .webp({ quality: 80 })
        .toFile(webpPath)
      console.log(`✓ ${img.name}.webp created`)

      // 生成移动端 WebP（50% 缩放，质量 80%）
      await sharp(jpgPath)
        .resize(Math.round(img.width * 0.5), Math.round(img.height * 0.5))
        .webp({ quality: 80 })
        .toFile(mobileWebpPath)
      console.log(`✓ ${img.name}-mobile.webp created`)

      // 生成移动端 JPG（50% 缩放，质量 85%）
      await sharp(jpgPath)
        .resize(Math.round(img.width * 0.5), Math.round(img.height * 0.5))
        .jpeg({ quality: 85 })
        .toFile(mobileJpgPath)
      console.log(`✓ ${img.name}-mobile.jpg created`)

    } catch (err) {
      console.error(`✗ Error processing ${img.name}:`, err.message)
    }
  }
  console.log('\nAll images processed!')
}

convertImages()
