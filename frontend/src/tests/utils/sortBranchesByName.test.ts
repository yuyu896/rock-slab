import { describe, it, expect } from 'vitest'
import { sortBranchesByName } from '@/utils/sortBranchesByName'

describe('sortBranchesByName 分公司拼音排序', () => {
  it('按 label 拼音序排列且不改原数组', () => {
    // 北京(B/5317) 广州(G/5E7F) 杭州(H/676D)：拼音序与码点序一致，
    // 断言在任何 CJK collation（浏览器 pinyin / Node 回退）下都稳定
    const raw = [
      { value: '1', label: '杭州分公司' },
      { value: '2', label: '北京分公司' },
      { value: '3', label: '广州分公司' },
    ]
    const sorted = sortBranchesByName(raw)
    expect(sorted.map(o => o.label)).toEqual(['北京分公司', '广州分公司', '杭州分公司'])
    expect(raw[0].label).toBe('杭州分公司') // 原数组不动
  })

  it('兼容 { name } 形状', () => {
    const sorted = sortBranchesByName([{ name: '杭州分公司' }, { name: '广州分公司' }])
    expect(sorted.map(o => o.name)).toEqual(['广州分公司', '杭州分公司'])
  })
})
