## ADDED Requirements

### Requirement: 磐盘专属品牌 logo（资产层叠概念）

系统 MUST 提供专属品牌 logo，采用「资产层叠」概念（堆叠的盒 / 箱体轮廓，可含勾选点缀隐喻盘点）。logo MUST 为 SVG 矢量，封装为可复用组件（`BrandLogo`），支持单色（`mono`，随 `currentColor`）与品牌色（`brand`，渐变）两种变体及尺寸控制。

#### Scenario: logo 组件可复用且支持双变体

- **WHEN** 在任意位置需要展示 logo
- **THEN** `BrandLogo` 组件渲染「资产层叠」SVG，可按场景选择 `mono`（随主题变色）或 `brand`（品牌色渐变）变体，并按需控制尺寸

### Requirement: logo 全站统一应用

浏览器 favicon、PC 侧边栏顶部、登录页 MUST 统一使用该品牌 logo，MUST NOT 残留原通用立方体图标。

#### Scenario: 全站品牌一致

- **WHEN** 用户浏览任意页面或查看浏览器标签
- **THEN** favicon、侧边栏顶部、登录页均显示磐盘品牌 logo，无旧通用图标残留

### Requirement: logo 深色模式与多背景自适应

logo MUST 通过 `currentColor` 与设计令牌着色，在浅色 / 深色模式及不同背景（侧边栏深色、登录页品牌色、favicon）下均可辨，MUST NOT 写死颜色。

#### Scenario: 深色模式与不同背景下可辨

- **WHEN** 系统切换深色模式，或 logo 出现在侧边栏 / 登录页 / favicon 等不同背景
- **THEN** logo 配色自适应，对比度清晰可辨
