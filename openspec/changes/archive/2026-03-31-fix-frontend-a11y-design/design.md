# 技术设计：前端可访问性与设计系统修复

## Context

### 背景
前端设计审计（2026-03-31）发现可访问性得分 2/4，主要问题集中在：
- 表单控件缺少关联标签
- 键盘焦点样式缺失
- 模态框缺少 ARIA 语义和焦点管理
- 部分硬编码颜色未使用设计令牌

### 当前状态
- 已有完整的 CSS 变量系统 (`variables.css`)
- 使用 Vue 3 + TypeScript
- 表单组件分散在各个页面中，无统一封装
- 模态框使用自定义实现，无统一组件

### 约束
- 不引入新的 UI 框架或组件库
- 保持现有功能不变，仅增强可访问性
- 兼容 IE11+ 的 CSS 特性（使用 @supports 检测）

### 利益相关者
- 前端开发团队
- 产品团队（验收 WCAG 合规）
- 残障用户（直接受益）

## Goals / Non-Goals

**Goals:**
1. 达到 WCAG 2.1 AA 级别合规
2. 所有交互元素支持键盘操作
3. 统一设计令牌使用
4. 建立 `.impeccable.md` 设计上下文

**Non-Goals:**
1. 不重构组件架构（不抽取公共组件）
2. 不添加新的业务功能
3. 不修改后端 API
4. 不处理国际化 (i18n)

## Decisions

### D1: 使用原生 `:focus-visible` 而非 polyfill

**选择**: 使用 CSS `:focus-visible` 伪类
**原因**:
- 现代浏览器（Chrome 86+, Firefox 85+, Safari 15.4+）原生支持
- 自动区分键盘和鼠标焦点
- 无需 JavaScript 检测

**备选方案**:
- `what-input` 库：增加依赖，过度工程
- 轮廓样式同时应用于 `:focus` 和 `:focus-visible`：鼠标点击也会显示焦点环，体验不佳

**实现**:
```css
/* 基础焦点样式 */
:focus-visible {
  outline: 2px solid var(--color-primary-500);
  outline-offset: 2px;
}

/* 移除鼠标点击的焦点样式 */
:focus:not(:focus-visible) {
  outline: none;
}
```

### D2: 模态框焦点管理策略

**选择**: 使用 Vue 3 组合式函数 (Composable) 封装焦点陷阱
**原因**:
- 可复用于所有模态框
- 响应式自动清理
- 不依赖外部库

**备选方案**:
- `focus-trap` npm 包：功能完善但增加 4KB gzip
- 原生 `inert` 属性：浏览器支持有限

**实现**:
```typescript
// composables/useFocusTrap.ts
export function useFocusTrap(containerRef: Ref<HTMLElement | null>) {
  const focusableSelectors = [
    'button:not([disabled])',
    'input:not([disabled])',
    'select:not([disabled])',
    'textarea:not([disabled])',
    'a[href]',
    '[tabindex]:not([tabindex="-1"])'
  ].join(',')

  const handleKeydown = (e: KeyboardEvent) => {
    if (e.key !== 'Tab' || !containerRef.value) return
    const focusables = containerRef.value.querySelectorAll(focusableSelectors)
    const first = focusables[0] as HTMLElement
    const last = focusables[focusables.length - 1] as HTMLElement

    if (e.shiftKey && document.activeElement === first) {
      e.preventDefault()
      last.focus()
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault()
      first.focus()
    }
  }

  onMounted(() => {
    document.addEventListener('keydown', handleKeydown)
    // 自动聚焦第一个可聚焦元素
    const first = containerRef.value?.querySelector(focusableSelectors) as HTMLElement
    first?.focus()
  })

  onUnmounted(() => {
    document.removeEventListener('keydown', handleKeydown)
  })
}
```

### D3: 表单标签关联方案

**选择**: 使用显式 `<label for="id">` 关联
**原因**:
- 屏幕阅读器标准支持
- 点击标签聚焦输入框（增大点击区域）
- 无需修改现有组件结构

**备选方案**:
- 隐式包装 `<label><input/></label>`：需要重构大量代码
- `aria-label` 属性：不增加点击区域

**实现模式**:
```vue
<div class="form-group">
  <label class="form-label" for="phone">手机号</label>
  <input id="phone" v-model="phone" type="tel" class="form-input" />
</div>
```

### D4: 状态颜色令牌化

**选择**: 在 `variables.css` 中定义语义化状态颜色变量
**原因**:
- 统一管理，支持主题切换
- 便于深色模式适配

**实现**:
```css
:root {
  /* 状态色 - 在库 */
  --color-status-in-stock-bg: var(--color-primary-100);
  --color-status-in-stock-text: var(--color-primary-700);

  /* 状态色 - 使用中 */
  --color-status-in-use-bg: oklch(0.93 0.04 240);
  --color-status-in-use-text: oklch(0.45 0.15 240);

  /* 状态色 - 维修中 */
  --color-status-repair-bg: oklch(0.93 0.06 85);
  --color-status-repair-text: oklch(0.50 0.16 85);

  /* 状态色 - 报废 */
  --color-status-scrapped-bg: oklch(0.93 0.04 25);
  --color-status-scrapped-text: oklch(0.50 0.18 25);
}

@media (prefers-color-scheme: dark) {
  :root {
    --color-status-in-use-bg: oklch(0.25 0.06 240);
    --color-status-in-use-text: oklch(0.85 0.10 240);
    /* ... 其他深色模式调整 */
  }
}
```

## Risks / Trade-offs

| 风险 | 缓解措施 |
|------|----------|
| `:focus-visible` 在旧浏览器不支持 | 使用 `@supports` 检测，回退到 `:focus` 样式 |
| 焦点陷阱可能导致用户被困 | 添加 Escape 键关闭模态框功能 |
| 修改大量文件可能引入回归问题 | 分批次修改，每批次进行回归测试 |
| ID 冲突导致 label 关联错误 | 使用 Vue 的 `useId()` 或添加唯一前缀 |

## Migration Plan

### Phase 1: 基础设施 (Day 1)
1. 创建 `useFocusTrap` composable
2. 更新 `variables.css` 添加状态颜色令牌
3. 创建 `.impeccable.md` 设计上下文文件

### Phase 2: 全局样式 (Day 1)
1. 添加全局 `:focus-visible` 样式到 `global.css`
2. 添加 `prefers-reduced-motion` 媒体查询

### Phase 3: 组件修复 (Day 2-3)
1. 修复登录页表单标签
2. 修复分类页模态框和表单
3. 修复其他页面的交互元素

### Phase 4: 测试验证 (Day 3)
1. 键盘导航测试
2. 屏幕阅读器测试 (NVDA/VoiceOver)
3. 自动化可访问性审计 (axe-core)

### Rollback
- 每个阶段独立提交，可单独回滚
- 样式修改通过 CSS 文件回滚，不影响功能

## Open Questions

1. ~~是否需要支持屏幕阅读器的实时区域 (live regions)？~~ → 暂不支持，后续迭代
2. ~~触摸目标 44px 是否包括边距？~~ → 是的，触摸目标区域包括 padding/margin
3. 是否需要添加跳过导航链接 (skip to content)？→ 建议添加，但可在后续迭代
