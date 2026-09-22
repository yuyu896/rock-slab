/**
 * 分公司选项按名称拼音排序（branch-order-and-multi-filter）。
 * 中文拼音序只在可靠的前端做（localeCompare 'zh'）；后端 PG collation 按码点不可靠。
 * 适配两种形状：{ value, label }（筛选选项）与 { name }（分公司对象）。
 */
export function sortBranchesByName<T extends { label?: string; name?: string }>(list: T[]): T[] {
  return [...list].sort((a, b) => {
    const ka = a.label ?? a.name ?? ''
    const kb = b.label ?? b.name ?? ''
    return ka.localeCompare(kb, 'zh')
  })
}
