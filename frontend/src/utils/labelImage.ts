import QRCode from 'qrcode'

/** 标签规范 V1 的导出图片渲染：60×40 @203dpi×2 超采样，版式参数与 AssetPrintDialog 打印 CSS 同源（改动需两侧同步） */
export interface LabelAssetShape {
  内部编号: string
  序列号?: string
  资产名称?: string
  品目编号?: string
  分公司?: string
}

export const LABEL_SPEC = {
  widthMm: 60,
  heightMm: 40,
  /** ≈203dpi×2 超采样，取整为 16 px/mm（60×40 → 960×640） */
  pxPerMm: 16,
  paddingMm: 1.5,
  qrSizeMm: 13,
  qrQuietMm: 2,
  qrGapMm: 1.5,
  borderWidthMm: 0.3,
  lineGapMm: 0.6,
  lineHeightFactor: 1.25,
  fontMinMm: 2.2,
  fonts: {
    code: { sizeMm: 3.2, weight: '700', mono: true, color: '#000' },
    sn: { sizeMm: 2.8, weight: '400', mono: true, color: '#000' },
    name: { sizeMm: 3.0, weight: '600', mono: false, color: '#000' },
    aux: { sizeMm: 2.4, weight: '400', mono: false, color: '#444' },
  },
} as const

const MONO_FAMILY = 'Consolas, "Courier New", monospace'
const SANS_FAMILY = '"PingFang SC", "Microsoft YaHei", sans-serif'

export interface LabelLine {
  text: string
  sizeMm: number
  weight: string
  mono: boolean
  color: string
}

export interface MeasureFn {
  (text: string, font: { sizePx: number; weight: string; mono: boolean }): number
}

/** 三区文案行：SN 为空整行跳过（与打印版式同规则） */
export function buildLabelLines(asset: LabelAssetShape): LabelLine[] {
  const lines: LabelLine[] = [{ text: asset.内部编号, ...LABEL_SPEC.fonts.code }]
  if (asset.序列号) lines.push({ text: `SN: ${asset.序列号}`, ...LABEL_SPEC.fonts.sn })
  lines.push({ text: asset.资产名称 || '', ...LABEL_SPEC.fonts.name })
  lines.push({ text: `品目 ${asset.品目编号 || ''} · ${asset.分公司 || ''}`, ...LABEL_SPEC.fonts.aux })
  return lines
}

/** 超宽行缩号（步进 0.1mm，下限 2.2mm），保持单行不换行（与打印版式同规则） */
export function fitLines(lines: LabelLine[], measure: MeasureFn, maxTextWidthPx: number, pxPerMm: number): void {
  lines.forEach(line => {
    const fontOf = (sizePx: number) => ({ sizePx, weight: line.weight, mono: line.mono })
    while (line.sizeMm > LABEL_SPEC.fontMinMm && measure(line.text, fontOf(line.sizeMm * pxPerMm)) > maxTextWidthPx) {
      line.sizeMm = Math.round((line.sizeMm - 0.1) * 10) / 10
    }
  })
}

export function labelTextWidthMm(): number {
  const { widthMm, paddingMm, qrSizeMm, qrQuietMm, qrGapMm } = LABEL_SPEC
  return widthMm - paddingMm - (qrSizeMm + qrQuietMm * 2) - qrGapMm - paddingMm
}

export function computeLabelLayout(asset: LabelAssetShape, measure: MeasureFn, pxPerMm: number) {
  const lines = buildLabelLines(asset)
  fitLines(lines, measure, labelTextWidthMm() * pxPerMm, pxPerMm)
  const blockHeightMm = lines.reduce(
    (sum, l) => sum + l.sizeMm * LABEL_SPEC.lineHeightFactor, 0,
  ) + (lines.length - 1) * LABEL_SPEC.lineGapMm
  const { heightMm, paddingMm, qrSizeMm, qrQuietMm, qrGapMm } = LABEL_SPEC
  return {
    lines,
    qrText: asset.内部编号,
    qrXMm: paddingMm + qrQuietMm,
    qrYMm: (heightMm - qrSizeMm) / 2,
    qrSizeMm,
    textXMm: paddingMm + qrSizeMm + qrQuietMm * 2 + qrGapMm,
    blockTopMm: (heightMm - blockHeightMm) / 2,
    blockHeightMm,
  }
}

function canvasFont(line: LabelLine, pxPerMm: number): string {
  const family = line.mono ? MONO_FAMILY : SANS_FAMILY
  return `${line.weight} ${Math.round(line.sizeMm * pxPerMm)}px ${family}`
}

/** 渲染单张标签为 canvas（960×640，白底黑字带边框）；QR 与打印通道同参（ECC M、13mm+2mm 静区） */
export async function renderLabelCanvas(asset: LabelAssetShape): Promise<HTMLCanvasElement> {
  const pxPerMm = LABEL_SPEC.pxPerMm
  const W = Math.round(LABEL_SPEC.widthMm * pxPerMm)
  const H = Math.round(LABEL_SPEC.heightMm * pxPerMm)
  const canvas = document.createElement('canvas')
  canvas.width = W
  canvas.height = H
  const ctx = canvas.getContext('2d')
  if (!ctx) throw new Error('canvas 2d context unavailable')

  ctx.fillStyle = '#fff'
  ctx.fillRect(0, 0, W, H)
  const bw = LABEL_SPEC.borderWidthMm * pxPerMm
  ctx.strokeStyle = '#999'
  ctx.lineWidth = bw
  ctx.strokeRect(bw / 2, bw / 2, W - bw, H - bw)

  const measure: MeasureFn = (text, font) => {
    ctx.font = `${font.weight} ${font.sizePx}px ${font.mono ? MONO_FAMILY : SANS_FAMILY}`
    return ctx.measureText(text).width
  }
  const layout = computeLabelLayout(asset, measure, pxPerMm)

  const qrCanvas = document.createElement('canvas')
  await QRCode.toCanvas(qrCanvas, layout.qrText, {
    errorCorrectionLevel: 'M',
    margin: 0,
    width: Math.round(layout.qrSizeMm * pxPerMm),
  })
  ctx.drawImage(
    qrCanvas,
    layout.qrXMm * pxPerMm,
    layout.qrYMm * pxPerMm,
    layout.qrSizeMm * pxPerMm,
    layout.qrSizeMm * pxPerMm,
  )

  let yMm = layout.blockTopMm
  layout.lines.forEach(line => {
    ctx.font = canvasFont(line, pxPerMm)
    ctx.fillStyle = line.color
    ctx.textBaseline = 'alphabetic'
    ctx.fillText(line.text, layout.textXMm * pxPerMm, (yMm + line.sizeMm) * pxPerMm)
    yMm += line.sizeMm * LABEL_SPEC.lineHeightFactor + LABEL_SPEC.lineGapMm
  })
  return canvas
}

export async function renderLabelDataUrl(asset: LabelAssetShape): Promise<string> {
  const canvas = await renderLabelCanvas(asset)
  return canvas.toDataURL('image/png')
}

export function labelFileName(asset: LabelAssetShape): string {
  return `标签_${asset.内部编号}.png`
}
