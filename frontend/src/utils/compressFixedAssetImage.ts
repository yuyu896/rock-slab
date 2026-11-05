const MAX_IMAGE_EDGE = 2048
const MAX_IMAGE_SIZE = 1024 * 1024
const WEBP_QUALITY = 0.82

interface DecodedImage {
  source: CanvasImageSource
  width: number
  height: number
  close: () => void
}

async function decodeImage(file: File): Promise<DecodedImage> {
  if (typeof createImageBitmap === 'function') {
    try {
      const bitmap = await createImageBitmap(file)
      return {
        source: bitmap,
        width: bitmap.width,
        height: bitmap.height,
        close: () => bitmap.close(),
      }
    } catch {
      throw new Error('无法读取图片，请重新选择文件')
    }
  }

  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file)
    const image = new Image()
    image.onload = () => resolve({
      source: image,
      width: image.naturalWidth,
      height: image.naturalHeight,
      close: () => URL.revokeObjectURL(url),
    })
    image.onerror = () => {
      URL.revokeObjectURL(url)
      reject(new Error('无法读取图片，请重新选择文件'))
    }
    image.src = url
  })
}

/** Compress large fixed-asset photos before upload; smaller photos keep their original bytes. */
export async function compressFixedAssetImage(file: File): Promise<File> {
  const image = await decodeImage(file)
  try {
    const { width, height } = image
    if (!width || !height) throw new Error('无法读取图片尺寸，请重新选择文件')
    if (file.size <= MAX_IMAGE_SIZE && Math.max(width, height) <= MAX_IMAGE_EDGE) return file

    const scale = Math.min(1, MAX_IMAGE_EDGE / Math.max(width, height))
    const outputWidth = Math.max(1, Math.round(width * scale))
    const outputHeight = Math.max(1, Math.round(height * scale))
    const canvas = document.createElement('canvas')
    canvas.width = outputWidth
    canvas.height = outputHeight
    const context = canvas.getContext('2d')
    if (!context) throw new Error('浏览器无法处理这张图片，请换一张图片重试')
    context.drawImage(image.source, 0, 0, outputWidth, outputHeight)

    const blob = await new Promise<Blob>((resolve, reject) => {
      canvas.toBlob((result) => {
        if (!result) {
          reject(new Error('图片压缩失败，请重新选择文件'))
          return
        }
        resolve(result)
      }, 'image/webp', WEBP_QUALITY)
    })
    if (blob.type !== 'image/webp') {
      throw new Error('当前浏览器不支持 WebP 图片压缩，请更新浏览器后重试')
    }
    if (blob.size > 10 * 1024 * 1024) {
      throw new Error('压缩后的图片仍超过 10MB，请选择更小的图片')
    }

    const name = file.name.replace(/\.[^.]+$/, '') || 'image'
    return new File([blob], `${name}.webp`, { type: 'image/webp', lastModified: file.lastModified })
  } finally {
    image.close()
  }
}
