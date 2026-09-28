# 提案：标签导出图片（打印第二通道）

## Why

分公司统一使用汉印 M1 这类 App 生态的蓝牙标签机：无 Windows 驱动，浏览器打印管线（`window.print()`）够不着，V1 已建成的 60×40 标签版式对这类机器输出无门。此类机器的通用能力是"App 打印相册图片"——用一张按打印规范渲染的 PNG 图片做桥，即可让**所有** App 生态蓝牙标签机（不限汉印 M1，精臣/得力/芯烨等同样适用）打出规范标签，与既有浏览器打印通道（系统打印机：A4 普通打印机、有驱动的桌面标签机）形成并存的两条输出通道，分公司按手头硬件自选。

## What Changes

- 打印弹窗底部新增「导出图片」按钮（与「打印」并列为第二通道）
- 每张标签按 60×40 标准版式（QR + 三区文案，与打印版式同规范同参数）渲染为 PNG：203dpi 基准 ×2 超采样（960×640px），白底黑字
- 导出方式：**单张下载**（文件名含内部编号）+ **全部下载**（逐张触发，浏览器一次性授权）；手机浏览器上可长按导出预览图直接存相册
- 序列号为空的标签 PNG 同样隐藏 SN 行；超长行沿用缩号规则（canvas 侧等价实现）

## Capabilities

### New Capabilities

（无——并入标签打印能力）

### Modified Capabilities

- `fa-layout-and-print`: 「固定资产表标签打印」需求扩展双通道——浏览器打印之外新增图片导出通道，PNG 按 60×40/203dpi 渲染且内容与打印版式同规范，兼容任意 App 生态蓝牙标签机

## Impact

- 前端：`frontend/src/views/assets/AssetPrintDialog.vue`（导出入口与预览）、新增 `frontend/src/utils/labelImage.ts`（canvas 渲染，复用 `qrcode` 的 `toCanvas`）
- 测试：`AssetPrintDialog.test.ts` 扩展导出用例、`labelImage` 渲染单测
- 无新依赖（canvas + qrcode 现有）、无后端改动
