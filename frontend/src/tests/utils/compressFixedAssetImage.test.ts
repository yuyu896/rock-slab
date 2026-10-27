import { afterEach, describe, expect, it, vi } from 'vitest'
import { compressFixedAssetImage } from '@/utils/compressFixedAssetImage'

afterEach(() => {
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

describe('compressFixedAssetImage', () => {
  it('resizes large images, encodes WebP, and releases the decoded bitmap', async () => {
    const close = vi.fn()
    const drawImage = vi.fn()
    const toBlob = vi.fn((callback: BlobCallback, type?: string) => {
      callback(new Blob(['compressed'], { type }))
    })
    const canvas = {
      width: 0,
      height: 0,
      getContext: vi.fn(() => ({ drawImage })),
      toBlob,
    }
    const bitmap = { width: 4000, height: 2000, close }
    vi.stubGlobal('createImageBitmap', vi.fn().mockResolvedValue(bitmap))
    vi.spyOn(document, 'createElement').mockReturnValue(canvas as unknown as HTMLElement)

    const file = new File([new Uint8Array(2 * 1024 * 1024)], 'phone-photo.jpg', {
      type: 'image/jpeg',
      lastModified: 123,
    })
    const result = await compressFixedAssetImage(file)

    expect(canvas.width).toBe(2048)
    expect(canvas.height).toBe(1024)
    expect(drawImage).toHaveBeenCalledWith(bitmap, 0, 0, 2048, 1024)
    expect(toBlob).toHaveBeenCalledWith(expect.any(Function), 'image/webp', 0.82)
    expect(result.name).toBe('phone-photo.webp')
    expect(result.type).toBe('image/webp')
    expect(result.lastModified).toBe(123)
    expect(result.size).toBeLessThan(file.size)
    expect(close).toHaveBeenCalledOnce()
  })

  it('keeps small images unchanged', async () => {
    const close = vi.fn()
    vi.stubGlobal('createImageBitmap', vi.fn().mockResolvedValue({ width: 1200, height: 800, close }))
    const file = new File(['small'], 'small.jpg', { type: 'image/jpeg' })

    await expect(compressFixedAssetImage(file)).resolves.toBe(file)
    expect(close).toHaveBeenCalledOnce()
  })
})
