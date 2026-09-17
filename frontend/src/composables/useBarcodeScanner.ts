import { onBeforeUnmount, ref, type Ref } from 'vue'
import jsQR from 'jsqr'

export interface BarcodeScannerOptions {
  onDetect: (code: string) => void
  /** 识别轮询间隔，默认 400ms */
  intervalMs?: number
  /** 同码冷却窗口，默认 1000ms */
  cooldownMs?: number
}

export interface BarcodeScanner {
  active: Ref<boolean>
  error: Ref<string>
  engine: 'native' | 'jsqr'
  frames: Ref<number>
  resolution: Ref<string>
  lastError: Ref<string>
  start: () => Promise<void>
  stop: () => void
}

/** 同码冷却判定（纯函数便于单测） */
export function shouldAcceptCode(code: string, lastCode: string, lastTime: number, now: number, cooldownMs: number): boolean {
  return !(code === lastCode && now - lastTime < cooldownMs)
}

/**
 * 双引擎扫码：BarcodeDetector 优先（Android Chrome/Edge），jsQR canvas 解码兜底（iPhone Safari/微信）。
 * 显式 start/stop：调用方绑定「开始扫码」按钮，权限弹窗不前置；会话内识别成功不停机（连扫）。
 */
export function useBarcodeScanner(videoRef: Ref<HTMLVideoElement | null>, options: BarcodeScannerOptions): BarcodeScanner {
  const { onDetect, intervalMs = 400, cooldownMs = 1000 } = options
  const active = ref(false)
  const error = ref('')
  /** 调试可见性：帧计数、视频分辨率与最近识别错误（识别不出码时先看循环是否在跑） */
  const frames = ref(0)
  const resolution = ref('')
  const lastError = ref('')
  const supportsNative = typeof window !== 'undefined' && 'BarcodeDetector' in window

  let stream: MediaStream | null = null
  let timer: ReturnType<typeof setInterval> | null = null
  let detector: any = null
  let canvas: HTMLCanvasElement | null = null
  let lastCode = ''
  let lastTime = 0

  function stop() {
    active.value = false
    if (timer) {
      clearInterval(timer)
      timer = null
    }
    if (stream) {
      stream.getTracks().forEach(track => track.stop())
      stream = null
    }
    const video = videoRef.value
    if (video) video.srcObject = null
  }

  async function start() {
    if (active.value) return
    error.value = ''
    try {
      stream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: 'environment',
          // 小尺寸标签 QR 需要高分辨率帧：默认 VGA（640×480）下 QR 模块仅 ~2px，低于解码下限
          width: { ideal: 1920 },
          height: { ideal: 1080 },
        },
      })
    } catch (e) {
      error.value = `无法访问摄像头（${(e as Error).name}），请检查权限或改用手动输入`
      return
    }
    const video = videoRef.value
    if (!video) {
      stop()
      return
    }
    video.srcObject = stream
    active.value = true
    try {
      await video.play()
    } catch {
      // 部分浏览器 autoplay 受限时静默，取景仍可显示
    }
    timer = setInterval(() => void detectFrame(), intervalMs)
  }

  async function detectFrame() {
    const video = videoRef.value
    if (!video || !active.value || video.readyState < 2) return
    let code: string | null = null
    let frameError = ''
    if (supportsNative) {
      try {
        detector = detector ?? new (window as any).BarcodeDetector({ formats: ['qr_code'] })
        const barcodes = await detector.detect(video)
        code = barcodes[0]?.rawValue ?? null
      } catch (e) {
        frameError = `native:${(e as Error).name}`
      }
    }
    if (!code) {
      try {
        code = decodeWithJsQR(video)
      } catch (e) {
        frameError += ` jsqr:${(e as Error).name}`
      }
    }
    if (!code) {
      // 中央裁剪 50% 等效数码变焦：小尺寸标签 QR 模块像素翻倍
      try {
        code = decodeWithJsQR(video, 720, 0.5)
      } catch {
        // 裁剪路径失败静默
      }
    }
    lastError.value = frameError
    frames.value += 1
    resolution.value = `${video.videoWidth}×${video.videoHeight}`
    if (!code) return
    const now = Date.now()
    if (!shouldAcceptCode(code, lastCode, lastTime, now, cooldownMs)) return
    lastCode = code
    lastTime = now
    onDetect(code)
  }

  /** jsQR 兜底：canvas 抓帧，默认降采样到 720px；crop<1 时取中央裁剪（变焦增强） */
  function decodeWithJsQR(video: HTMLVideoElement, sampleWidth = 720, crop = 1): string | null {
    if (!video.videoWidth) return null
    canvas = canvas ?? document.createElement('canvas')
    const sw = video.videoWidth * crop
    const sh = video.videoHeight * crop
    const sx = (video.videoWidth - sw) / 2
    const sy = (video.videoHeight - sh) / 2
    const w = Math.min(sampleWidth, Math.round(sw))
    const h = Math.max(1, Math.round((w * sh) / sw))
    canvas.width = w
    canvas.height = h
    const ctx = canvas.getContext('2d', { willReadFrequently: true })
    if (!ctx) return null
    ctx.drawImage(video, sx, sy, sw, sh, 0, 0, w, h)
    const image = ctx.getImageData(0, 0, w, h)
    const found = jsQR(image.data, w, h, { inversionAttempts: 'dontInvert' })
    return found?.data ?? null
  }

  onBeforeUnmount(stop)

  return { active, error, engine: supportsNative ? 'native' : 'jsqr', frames, resolution, lastError, start, stop }
}
