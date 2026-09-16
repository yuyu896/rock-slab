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
  供应商: '联想',
  采购日期: '2026-08-15',
}

const PX_PER_MM = 16
/** 假测量：等宽字符 0.55 倍字号、非等宽 0.6 倍 */
const fakeMeasure = (text: string, font: { sizePx: number; mono: boolean }) =>
  text.length * font.sizePx * (font.mono ? 0.55 : 0.6)

describe('labelImage 布局计算', () => {
  it('V2 六行集：品目/分公司分行，供应商·采购日期合并行', () => {
    const lines = buildLabelLines(asset)
    expect(lines.map(l => l.text)).toEqual([
      'A-a00008-BJ001-1',
      'SN: PF3XK2LM',
      'ThinkPad T14',
      '品目 A-a00008',
      '北京分公司',
      '联想 · 2026-08-15',
    ])
  })

  it('SN 为空（待补录）整行跳过', () => {
    const lines = buildLabelLines({ ...asset, 序列号: '' })
    expect(lines.some(l => l.text.startsWith('SN:'))).toBe(false)
    expect(lines).toHaveLength(5)
  })

  it('供应商/采购日期空值形态：单项只留存在项、双空整行隐藏', () => {
    expect(buildLabelLines({ ...asset, 采购日期: '' }).at(-1)!.text).toBe('联想')
    expect(buildLabelLines({ ...asset, 供应商: '' }).at(-1)!.text).toBe('2026-08-15')
    const both = buildLabelLines({ ...asset, 供应商: '', 采购日期: '' })
    expect(both.at(-1)!.text).toBe('北京分公司')
    expect(both).toHaveLength(5)
  })

  it('超宽行缩号且不低于 2.2mm 下限', () => {
    const longBranch = '上海浦东金桥某超长名称分公司测试专用延伸字符一二三四五六七八九十'
    const lines = buildLabelLines({ ...asset, 分公司: longBranch })
    const branch = lines.find(l => l.text === longBranch)!
    expect(branch.sizeMm).toBe(LABEL_SPEC.fonts.aux.sizeMm)
    fitLines(lines, fakeMeasure, labelTextWidthMm() * PX_PER_MM, PX_PER_MM)
    expect(branch.sizeMm).toBeLessThan(LABEL_SPEC.fonts.aux.sizeMm)
    lines.forEach(l => expect(l.sizeMm).toBeGreaterThanOrEqual(LABEL_SPEC.fontMinMm))
  })

  it('不超宽的行保持原字号', () => {
    const lines = buildLabelLines(asset)
    const before = lines.map(l => l.sizeMm)
    fitLines(lines, fakeMeasure, labelTextWidthMm() * PX_PER_MM, PX_PER_MM)
    expect(lines.map(l => l.sizeMm)).toEqual(before)
  })

  it('布局几何与规范一致：QR 左置垂直居中、文字区 20mm 起、居中后上移 0.4mm', () => {
    const layout = computeLabelLayout(asset, fakeMeasure, PX_PER_MM)
    expect(layout.qrText).toBe('A-a00008-BJ001-1')
    expect(layout.qrXMm).toBeCloseTo(1.5 + 2, 5)
    expect(layout.qrYMm).toBeCloseTo((40 - 13) / 2, 5)
    expect(layout.textXMm).toBeCloseTo(20, 5)
    const centered = (40 - layout.blockHeightMm) / 2
    expect(layout.blockTopMm).toBeCloseTo(centered - 0.4, 5)
    expect(layout.blockTopMm).toBeGreaterThan(0)
    expect(layout.blockHeightMm).toBeLessThan(37)
  })

  it('文件名含内部编号', () => {
    expect(labelFileName(asset)).toBe('标签_A-a00008-BJ001-1.png')
  })
})
