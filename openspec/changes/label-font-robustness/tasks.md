# 标签字体根治 — 实施任务

## 1. 字体自托管

- [x] 1.1 `npm i @fontsource/jetbrains-mono`，入口引入 latin-400/600/700 三字重 css（Vite 打包 woff2 + @font-face "JetBrains Mono" 全局注册）
- [x] 1.2 `document.fonts.ready.then(fitLabelLines)` 补测（webfont 晚于首次测量的兜底重缩）

## 2. 缩号安全余量

- [x] 2.1 `labelImage.ts` 导出 `FIT_SAFETY_RATIO = 0.97`：打印通道 `fitLabelLines` 循环条件改 `scrollWidth > clientWidth * FIT_SAFETY_RATIO`；导出通道 `computeLabelLayout` 以 `labelTextWidthMm() * FIT_SAFETY_RATIO * pxPerMm` 为目标宽——单一来源同参

## 3. NO 行降粗

- [x] 3.1 `.paper-* .label-code` 字重 700→600；`LABEL_SPEC.fonts.code.weight` '700'→'600'（双源同笔）

## 4. 测试与验证

- [x] 4.1 契约断言：@fontsource 引入、FIT_SAFETY_RATIO 双侧使用、字重双源一致（600）；既有断言同步（labelImage 字重相关用例）
- [x] 4.2 全量 `npm run test` + `npm run build` 通过（构建产物含 woff2）
- [ ] 4.3 手验：**李雨霜电脑**复打 100+ 编号标签（本案回归判据）；另抽一台未装开发字体的普通办公机打印正常；导出图片通道回归

## 5. 收口

- [ ] 5.1 台州四项环境确认结果回填（触发点记录，虽不影响本修复）
- [ ] 5.2 部署后更新运维备忘（字体已自托管，环境差异论失效）
