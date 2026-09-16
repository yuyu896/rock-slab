import QRCode from 'qrcode'

/** 标签规范 V1 的导出图片渲染：60×40 @203dpi×2 超采样，版式参数与 AssetPrintDialog 打印 CSS 同源（改动需两侧同步） */
export interface LabelAssetShape {
  内部编号: string
  序列号?: string
  资产名称?: string
  品目编号?: string
  分公司?: string
  供应商?: string
  采购日期?: string
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
  lineGapMm: 0.5,
  lineHeightFactor: 1.2,
  /** 垂直居中后的整体上移量：抵消行盒下行空隙导致的视觉偏下 */
  blockLiftMm: 0.4,
  fontMinMm: 2.2,
  /** V3 英文字段前缀（统一带冒号；换词只改这里；打印 CSS 侧文案与此对齐，测试源码断言把关） */
  prefixes: { code: 'NO:', sn: 'SN:', name: 'ITEM:', branch: 'BRANCH:', vendor: 'VENDOR:', date: 'DATE:' },
  fonts: {
    code: { sizeMm: 3.4, weight: '700', mono: true, color: '#000' },
    sn: { sizeMm: 3.0, weight: '400', mono: true, color: '#000' },
    name: { sizeMm: 3.4, weight: '600', mono: false, color: '#000' },
    aux: { sizeMm: 2.6, weight: '400', mono: false, color: '#444' },
    prefix: { sizeMm: 2.6, weight: '400', mono: true, color: '#444' },
  },
} as const

const MONO_FAMILY = 'Consolas, "Courier New", monospace'
const SANS_FAMILY = '"PingFang SC", "Microsoft YaHei", sans-serif'

export interface LabelSegment {
  text: string
  sizeMm: number
  weight: string
  mono: boolean
  color: string
}

export interface LabelLine {
  segments: LabelSegment[]
  /** 行主字号 = 最大段字号，驱动行高与缩号基准 */
  sizeMm: number
}

export interface MeasureFn {
  (text: string, font: { sizePx: number; weight: string; mono: boolean }): number
}

function prefixed(prefix: string, value: string, valueFont: { sizeMm: number; weight: string; mono: boolean; color: string }): LabelSegment[] {
  return [
    { text: `${prefix} `, ...LABEL_SPEC.fonts.prefix },
    { text: value, ...valueFont },
  ]
}

function mkLine(segments: LabelSegment[]): LabelLine {
  return { segments, sizeMm: Math.max(...segments.map(s => s.sizeMm)) }
}

/** V3 五行英文前缀行集：品目编号行已删（内部编号首段即品目码）；空值行隐藏（与打印版式同规则） */
export function buildLabelLines(asset: LabelAssetShape): LabelLine[] {
  const P = LABEL_SPEC.prefixes
  const lines: LabelLine[] = [mkLine(prefixed(P.code, asset.内部编号, LABEL_SPEC.fonts.code))]
  if (asset.序列号) lines.push(mkLine(prefixed(P.sn, asset.序列号, LABEL_SPEC.fonts.sn)))
  lines.push(mkLine(prefixed(P.name, asset.资产名称 || '', LABEL_SPEC.fonts.name)))
  if (asset.分公司) lines.push(mkLine(prefixed(P.branch, asset.分公司, LABEL_SPEC.fonts.aux)))
  const tail: LabelSegment[] = []
  if (asset.供应商) tail.push(...prefixed(P.vendor, asset.供应商, LABEL_SPEC.fonts.aux))
  if (asset.供应商 && asset.采购日期) tail.push({ text: '  ', ...LABEL_SPEC.fonts.aux })
  if (asset.采购日期) tail.push(...prefixed(P.date, asset.采购日期, LABEL_SPEC.fonts.aux))
  if (tail.length) lines.push(mkLine(tail))
  return lines
}

/** 行拼接文案（测试与调试用） */
export function flattenLine(line: LabelLine): string {
  return line.segments.map(s => s.text).join('')
}

/** 超宽行按比例缩号（步进 0.1mm 作用于行主字号，下限 2.2mm），保持单行不换行（与打印版式同规则） */
export function fitLines(lines: LabelLine[], measure: MeasureFn, maxTextWidthPx: number, pxPerMm: number): void {
  lines.forEach(line => {
    const widthOf = () => line.segments.reduce((sum, s) =>
      sum + measure(s.text, { sizePx: s.sizeMm * pxPerMm, weight: s.weight, mono: s.mono }), 0)
    while (widthOf() > maxTextWidthPx && line.sizeMm > LABEL_SPEC.fontMinMm) {
      const factor = (line.sizeMm - 0.1) / line.sizeMm
      line.sizeMm = Math.round((line.sizeMm - 0.1) * 10) / 10
      line.segments.forEach(s => {
        s.sizeMm = Math.round(s.sizeMm * factor * 100) / 100
      })
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
  const { heightMm, paddingMm, qrSizeMm, qrQuietMm, qrGapMm, blockLiftMm } = LABEL_SPEC
  return {
    lines,
    qrText: asset.内部编号,
    qrXMm: paddingMm + qrQuietMm,
    qrYMm: (heightMm - qrSizeMm) / 2,
    qrSizeMm,
    textXMm: paddingMm + qrSizeMm + qrQuietMm * 2 + qrGapMm,
    blockTopMm: (heightMm - blockHeightMm) / 2 - blockLiftMm,
    blockHeightMm,
  }
}

function canvasFont(seg: LabelSegment, pxPerMm: number): string {
  const family = seg.mono ? MONO_FAMILY : SANS_FAMILY
  return `${seg.weight} ${Math.round(seg.sizeMm * pxPerMm)}px ${family}`
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
    let xPx = layout.textXMm * pxPerMm
    const baselinePx = (yMm + line.sizeMm) * pxPerMm
    ctx.textBaseline = 'alphabetic'
    line.segments.forEach(seg => {
      ctx.font = canvasFont(seg, pxPerMm)
      ctx.fillStyle = seg.color
      ctx.fillText(seg.text, xPx, baselinePx)
      xPx += ctx.measureText(seg.text).width
    })
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
