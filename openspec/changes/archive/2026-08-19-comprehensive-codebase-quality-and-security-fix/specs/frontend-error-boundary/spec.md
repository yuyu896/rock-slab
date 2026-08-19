## ADDED Requirements

### Requirement: Vue 全局错误处理
系统 SHALL 在 `main.ts` 中注册 `app.config.errorHandler` 和 `app.config.handler`，捕获未处理的组件错误，防止整个应用崩溃。

#### Scenario: 组件运行时错误
- **WHEN** 某个 Vue 组件在渲染或事件处理中抛出未捕获的异常
- **THEN** 全局错误处理器 SHALL 捕获该错误，显示 Element Plus 错误提示，并阻止错误向上传播导致白屏

#### Scenario: 错误不影响其他组件
- **WHEN** 组件 A 发生运行时错误
- **THEN** 组件 B SHALL 继续正常工作，不受组件 A 错误的影响

### Requirement: Store 错误处理统一
所有 Pinia store 的异步操作 SHALL 遵循统一的错误处理模式：使用 `try/catch` 包裹，catch 中调用 `handleApiError()` 显示错误提示，并通过 `error` ref 暴露错误状态。

#### Scenario: Store API 调用失败
- **WHEN** store action 中的 API 调用返回非 2xx 状态码
- **THEN** store SHALL 设置 `error` ref 为错误信息，并显示 Element Plus 错误提示

#### Scenario: Store 加载状态正确管理
- **WHEN** store action 执行中发生异常
- **THEN** `loading` ref SHALL 在 `finally` 块中被重置为 false，避免界面永久加载状态
