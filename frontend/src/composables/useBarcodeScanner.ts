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
        video: { facingMode: 'environment' },
      })
    } catch {
      error.value = '无法访问摄像头，请检查权限设置，或使用手动输入'
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
    try {
      if (supportsNative) {
        detector = detector ?? new (window as any).BarcodeDetector({ formats: ['qr_code'] })
        const barcodes = await detector.detect(video)
        code = barcodes[0]?.rawValue ?? null
      } else {
        code = decodeWithJsQR(video)
      }
    } catch {
      // 单帧识别失败忽略，下一轮重试
    }
    if (!code) return
    const now = Date.now()
    if (!shouldAcceptCode(code, lastCode, lastTime, now, cooldownMs)) return
    lastCode = code
    lastTime = now
    onDetect(code)
  }

  /** jsQR 兜底：canvas 抓帧降采样到 480px 宽再解码（CPU 可控） */
  function decodeWithJsQR(video: HTMLVideoElement): string | null {
    if (!video.videoWidth) return null
    canvas = canvas ?? document.createElement('canvas')
    const w = 480
    const h = Math.max(1, Math.round((480 * video.videoHeight) / video.videoWidth))
    canvas.width = w
    canvas.height = h
    const ctx = canvas.getContext('2d', { willReadFrequently: true })
    if (!ctx) return null
    ctx.drawImage(video, 0, 0, w, h)
    const image = ctx.getImageData(0, 0, w, h)
    const found = jsQR(image.data, w, h, { inversionAttempts: 'dontInvert' })
    return found?.data ?? null
  }

  onBeforeUnmount(stop)

  return { active, error, engine: supportsNative ? 'native' : 'jsqr', start, stop }
}
