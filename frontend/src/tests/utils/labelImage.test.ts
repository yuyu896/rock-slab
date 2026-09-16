import { describe, it, expect } from 'vitest'
import {
  LABEL_SPEC,
  buildLabelLines,
  computeLabelLayout,
  fitLines,
  flattenLine,
  labelFileName,
  labelTextWidthMm,
} from '@/utils/labelImage'

const asset = {
  内部编号: 'A-a00008-BJ001-1',
  序列号: 'PF3XK2LM',
  资产名称: 'ThinkPad T14',
  品目编号: 'A-a00008',
  分公司: '北京分公司',
  供应商: '小熊',
  采购日期: '2026-09-16',
}

const PX_PER_MM = 16
/** 假测量：等宽字符 0.55 倍字号、非等宽 0.6 倍 */
const fakeMeasure = (text: string, font: { sizePx: number; mono: boolean }) =>
  text.length * font.sizePx * (font.mono ? 0.55 : 0.6)

describe('labelImage V3 布局计算', () => {
  it('五行英文前缀行集（前缀统一带冒号，品目编号行已删）', () => {
    const lines = buildLabelLines(asset)
    expect(lines.map(flattenLine)).toEqual([
      'NO: A-a00008-BJ001-1',
      'SN: PF3XK2LM',
      'ITEM: ThinkPad T14',
      'BRANCH: 北京分公司',
      'VENDOR: 小熊  DATE: 2026-09-16',
    ])
  })

  it('首行混合字号：前缀 2.6mm、主码 3.4mm', () => {
    const [codeLine] = buildLabelLines(asset)
    expect(codeLine.sizeMm).toBe(3.4)
    expect(codeLine.segments[0]).toMatchObject({ text: 'NO: ', sizeMm: 2.6 })
    expect(codeLine.segments[1]).toMatchObject({ text: 'A-a00008-BJ001-1', sizeMm: 3.4 })
  })

  it('SN 为空（待补录）整行跳过', () => {
    const lines = buildLabelLines({ ...asset, 序列号: '' })
    expect(lines.some(l => flattenLine(l).startsWith('SN:'))).toBe(false)
    expect(lines).toHaveLength(4)
  })

  it('供应商/采购日期空值形态：单项只留存在项、双空整行隐藏', () => {
    expect(flattenLine(buildLabelLines({ ...asset, 采购日期: '' }).at(-1)!)).toBe('VENDOR: 小熊')
    expect(flattenLine(buildLabelLines({ ...asset, 供应商: '' }).at(-1)!)).toBe('DATE: 2026-09-16')
    const both = buildLabelLines({ ...asset, 供应商: '', 采购日期: '' })
    expect(flattenLine(both.at(-1)!)).toBe('BRANCH: 北京分公司')
    expect(both).toHaveLength(4)
  })

  it('超宽行按比例缩号且不低于 2.2mm 下限', () => {
    const longBranch = '上海浦东金桥某超长名称分公司测试专用延伸字符一二三四五六七八九十一'
    const lines = buildLabelLines({ ...asset, 分公司: longBranch })
    const branch = lines.find(l => l.segments.some(s => s.text === longBranch))!
    const before = branch.segments.map(s => s.sizeMm)
    fitLines(lines, fakeMeasure, labelTextWidthMm() * PX_PER_MM, PX_PER_MM)
    expect(branch.segments[1].sizeMm).toBeLessThan(before[1])
    lines.forEach(l => {
      l.segments.forEach(s => expect(s.sizeMm).toBeGreaterThanOrEqual(LABEL_SPEC.fontMinMm))
    })
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
