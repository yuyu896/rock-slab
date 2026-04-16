/* 磐盘 - 头像渲染工具 */

/** 预设头像配色方案 */
const AVATAR_COLORS = [
  { bg: '#4F46E5', shapes: ['#6366F1', '#818CF8'] },  // geo-1 indigo
  { bg: '#0D9488', shapes: ['#14B8A6', '#5EEAD4'] },  // geo-2 teal
  { bg: '#D97706', shapes: ['#F59E0B', '#FCD34D'] },  // geo-3 amber
  { bg: '#E11D48', shapes: ['#F43F5E', '#FDA4AF'] },  // geo-4 rose
  { bg: '#7C3AED', shapes: ['#8B5CF6', '#C4B5FD'] },  // geo-5 violet
  { bg: '#059669', shapes: ['#10B981', '#6EE7B7'] },  // geo-6 emerald
  { bg: '#EA580C', shapes: ['#F97316', '#FDBA74'] },  // geo-7 orange
  { bg: '#0891B2', shapes: ['#06B6D4', '#67E8F9'] },  // geo-8 cyan
  { bg: '#2563EB', shapes: ['#3B82F6', '#93C5FD'] },  // geo-9 blue
  { bg: '#475569', shapes: ['#64748B', '#CBD5E1'] },  // geo-10 slate
] as const

/** 生成预设头像 SVG 字符串 */
export function getSystemAvatarSvg(key: string, size: number = 48): string {
  const idx = parseInt(key.replace('geo-', ''), 10) - 1
  if (idx < 0 || idx >= AVATAR_COLORS.length) return ''
  const { bg, shapes } = AVATAR_COLORS[idx]
  const patterns = [
    // geo-1: concentric circles
    `<circle cx="50" cy="50" r="35" fill="${shapes[0]}"/><circle cx="50" cy="50" r="20" fill="${shapes[1]}"/>`,
    // geo-2: offset squares
    `<rect x="15" y="15" width="40" height="40" rx="4" fill="${shapes[0]}"/><rect x="30" y="30" width="30" height="30" rx="4" fill="${shapes[1]}"/>`,
    // geo-3: triangle + circle
    `<polygon points="50,15 85,75 15,75" fill="${shapes[0]}"/><circle cx="50" cy="55" r="18" fill="${shapes[1]}"/>`,
    // geo-4: diagonal split
    `<rect width="100" height="100" fill="${shapes[0]}"/><polygon points="0,0 100,0 0,100" fill="${shapes[1]}"/>`,
    // geo-5: 4 dots
    `<circle cx="30" cy="30" r="14" fill="${shapes[0]}"/><circle cx="70" cy="30" r="14" fill="${shapes[1]}"/><circle cx="30" cy="70" r="14" fill="${shapes[1]}"/><circle cx="70" cy="70" r="14" fill="${shapes[0]}"/>`,
    // geo-6: rounded cross
    `<rect x="35" y="15" width="30" height="70" rx="8" fill="${shapes[0]}"/><rect x="15" y="35" width="70" height="30" rx="8" fill="${shapes[1]}"/>`,
    // geo-7: half circle + dot
    `<circle cx="50" cy="50" r="35" fill="${shapes[0]}"/><rect x="0" y="0" width="100" height="50" fill="${bg}"/><circle cx="50" cy="25" r="12" fill="${shapes[1]}"/>`,
    // geo-8: diamond
    `<polygon points="50,10 90,50 50,90 10,50" fill="${shapes[0]}"/><polygon points="50,25 75,50 50,75 25,50" fill="${shapes[1]}"/>`,
    // geo-9: horizontal stripes
    `<rect width="100" height="33" fill="${shapes[0]}"/><rect y="33" width="100" height="34" fill="${shapes[1]}"/><rect y="67" width="100" height="33" fill="${shapes[0]}"/>`,
    // geo-10: hexagon
    `<polygon points="50,10 88,30 88,70 50,90 12,70 12,30" fill="${shapes[0]}"/><polygon points="50,25 73,37 73,63 50,75 27,63 27,37" fill="${shapes[1]}"/>`,
  ]
  return `<svg viewBox="0 0 100 100" width="${size}" height="${size}" xmlns="http://www.w3.org/2000/svg"><rect width="100" height="100" rx="50" fill="${bg}"/>${patterns[idx]}</svg>`
}

/** 判断是否有有效的系统预设头像 */
export function hasSystemAvatar(key?: string | null): boolean {
  if (!key) return false
  return /^geo-\d+$/.test(key) && parseInt(key.replace('geo-', ''), 10) >= 1 && parseInt(key.replace('geo-', ''), 10) <= 10
}

/** 头像渲染优先级：avatar > system_avatar > 姓名首字母 */
export function getAvatarDisplay(
  avatar?: string | null,
  systemAvatar?: string | null,
  name: string = ''
): { type: 'image'; src: string } | { type: 'system'; key: string } | { type: 'initial'; letter: string } {
  if (avatar) return { type: 'image', src: avatar }
  if (hasSystemAvatar(systemAvatar)) return { type: 'system', key: systemAvatar! }
  return { type: 'initial', letter: name.charAt(0) || '?' }
}
