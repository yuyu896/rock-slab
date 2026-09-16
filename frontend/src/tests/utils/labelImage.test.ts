import { describe, it, expect } from 'vitest'
import {
  LABEL_SPEC,
  buildLabelLines,
  computeLabelLayout,
  fitLines,
  labelFileName,
  labelTextWidthMm,
} from '@/utils/labelImage'

const asset = {
  内部编号: 'A-a00008-BJ001-1',
  序列号: 'PF3XK2LM',
  资产名称: 'ThinkPad T14',
  品目编号: 'A-a00008',
  分公司: '北京分公司',
}

const PX_PER_MM = 16
/** 假测量：等宽字符 0.55 倍字号、非等宽 0.6 倍 */
const fakeMeasure = (text: string, font: { sizePx: number; mono: boolean }) =>
  text.length * font.sizePx * (font.mono ? 0.55 : 0.6)

describe('labelImage 布局计算', () => {
  it('三区文案行齐全（含 SN）', () => {
    const lines = buildLabelLines(asset)
    expect(lines.map(l => l.text)).toEqual([
      'A-a00008-BJ001-1',
      'SN: PF3XK2LM',
      'ThinkPad T14',
      '品目 A-a00008 · 北京分公司',
    ])
  })

  it('SN 为空（待补录）整行跳过', () => {
    const lines = buildLabelLines({ ...asset, 序列号: '' })
    expect(lines.some(l => l.text.startsWith('SN:'))).toBe(false)
    expect(lines).toHaveLength(3)
  })

  it('超宽行缩号且不低于 2.2mm 下限', () => {
    const long = { ...asset, 分公司: '上海浦东金桥某超长名称分公司测试专用' }
    const lines = buildLabelLines(long)
    const aux = lines[lines.length - 1]
    expect(aux.sizeMm).toBe(LABEL_SPEC.fonts.aux.sizeMm)
    fitLines(lines, fakeMeasure, labelTextWidthMm() * PX_PER_MM, PX_PER_MM)
    expect(aux.sizeMm).toBeLessThan(LABEL_SPEC.fonts.aux.sizeMm)
    lines.forEach(l => expect(l.sizeMm).toBeGreaterThanOrEqual(LABEL_SPEC.fontMinMm))
  })

  it('不超宽的行保持原字号', () => {
    const lines = buildLabelLines(asset)
    const before = lines.map(l => l.sizeMm)
    fitLines(lines, fakeMeasure, labelTextWidthMm() * PX_PER_MM, PX_PER_MM)
    expect(lines.map(l => l.sizeMm)).toEqual(before)
  })

  it('布局几何与规范一致：QR 左置垂直居中、文字区 20mm 起', () => {
    const layout = computeLabelLayout(asset, fakeMeasure, PX_PER_MM)
    expect(layout.qrText).toBe('A-a00008-BJ001-1')
    expect(layout.qrXMm).toBeCloseTo(1.5 + 2, 5)
    expect(layout.qrYMm).toBeCloseTo((40 - 13) / 2, 5)
    expect(layout.textXMm).toBeCloseTo(20, 5)
    expect(layout.blockTopMm).toBeGreaterThan(0)
    expect(layout.blockHeightMm).toBeLessThan(37)
  })

  it('文件名含内部编号', () => {
    expect(labelFileName(asset)).toBe('标签_A-a00008-BJ001-1.png')
  })
})
