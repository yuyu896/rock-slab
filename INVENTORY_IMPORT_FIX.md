# 盘点导入无响应问题修复

## 问题描述

生产环境中，盘点模块的 Excel 导入功能出现"无响应"问题：
- 用户点击"导入"按钮选择文件后，第一次导入正常
- 再次点击"导入"按钮时，选择**相同文件**没有任何反应
- 选择**不同文件**可以正常导入

**重要说明**：本问题是**纯 UI 交互 bug**，不影响业务逻辑。系统本身**支持重复导入**（通过 `repeat_rule` 配置），只是前端文件选择器状态管理有缺陷导致无法触发。

## 根本原因

**前端文件输入框状态管理缺陷**：

在 `frontend/src/views/Inventory.vue` 的 `handleImportFile` 函数中：

```typescript
// 问题代码（第 602-604 行）
} finally {
  importingTaskId.value = null
  // ❌ 缺少：input.value = ''
}
```

**问题流程**：
1. 用户选择文件 A → 导入成功
2. `finally` 块执行 `importingTaskId.value = null`，但 **`input.value` 仍保留文件 A**
3. 用户再次点击导入，选择相同文件 A
4. 浏览器检测到 `<input type="file">` 的值未变化，**不触发 `change` 事件**
5. `handleImportFile` 函数未被调用 → 用户感觉"无响应"

## 修复方案

在 `finally` 块中清空文件输入框的值：

```typescript
// 修复后（第 602-605 行）
} finally {
  importingTaskId.value = null
  input.value = ''  // ✅ 新增：确保每次都能重新选择文件
}
```

## 修复效果

- ✅ 用户可以连续导入同一个文件（常见场景：修正后重新导入）
- ✅ 每次点击"导入"都会触发文件选择对话框
- ✅ 无论选择什么文件，`change` 事件都会正常触发

## 重复导入的业务处理

系统已有完善的重复导入处理机制，通过盘点任务的 `repeat_rule` 字段控制：

### 1. `last` - 以最后一次为准（默认模式）
- **行为**：重复导入同一行数据会**覆盖**之前的结果
- **适用场景**：修正错误后重新导入（最常见）
- **示例**：第一次导入数量 10，第二次导入数量 15 → 最终结果 **15**

### 2. `accumulate` - 累计数量
- **行为**：重复导入同一行数据会**累加**数量
- **适用场景**：多人分区盘点，分批导入累计
- **示例**：第一次导入数量 10，第二次导入数量 15 → 最终结果 **25**

### 审计追踪

无论哪种模式，每次导入都会：
- 增加盘点次数计数 (`check_count`)
- 创建独立的盘点记录 (`InventoryCheck`)
- 记录操作人和操作时间

这确保了**完整的审计日志**，管理员可以在"盘点记录"中查看：
- 谁在什么时候盘了多少次
- 每次盘点的具体数量
- 最终采用的结果

### 实际应用

**场景一**：用户发现导入的数量有误
1. 修正 Excel 文件中的错误数据
2. 重新导入同一文件
3. 系统按 `last` 模式覆盖为正确数量
4. ✅ 无需删除任务重建，直接修正

**场景二**：三个仓管员分区盘点
1. 仓管 A 导入 1-100 号货架的盘点结果
2. 仓管 B 导入 101-200 号货架的盘点结果
3. 仓管 C 导入 201-300 号货架的盘点结果
4. ✅ 三次导入互不影响（不同资产编号），或按 `accumulate` 模式累加同一资产的多次盘点

## 相关文件

- `frontend/src/views/Inventory.vue` (第 605 行)

## 测试建议

**手动测试步骤**：
1. 创建一个盘点任务并开始盘点
2. 下载盘点模板，填写数据后导入 → 应成功
3. **不修改文件**，再次点击导入，选择相同文件 → 应正常弹出确认对话框并导入
4. 重复步骤 3 多次，确保每次都能正常导入

**自动化测试**（建议补充）：
```typescript
// frontend/src/tests/views/Inventory.test.ts
test('should allow importing the same file multiple times', async () => {
  const file = new File(['test'], 'test.xlsx')
  const input = screen.getByRole('file-input') as HTMLInputElement
  
  // First import
  await userEvent.upload(input, file)
  expect(input.value).toBe('') // Should be cleared
  
  // Second import with same file
  await userEvent.upload(input, file)
  expect(input.value).toBe('') // Should be cleared again
})
```

## 部署注意事项

1. 本次修改**仅涉及前端代码**，无需迁移数据库
2. 部署后需清理浏览器缓存或等待 CDN 更新
3. 建议在测试环境验证后再部署生产

## 其他发现

在代码审查过程中，还发现了以下可优化点（非本次修复范围）：

1. **取消选择文件的检测机制**（第 509-514 行）：
   - 使用 `setTimeout(..., 0)` 检测用户取消文件选择
   - 在某些浏览器中可能不可靠，建议使用 `focus` 事件监听

2. **错误处理可增强**：
   - 当前对网络错误、文件格式错误、业务逻辑错误都有处理
   - 可考虑添加更详细的日志记录，方便排查生产问题

3. **后端事务管理**：
   - `import_result` 视图使用 `@transaction.atomic` + 手动 savepoint
   - 当前实现正确，但复杂度较高，未来可考虑简化

## 修复日期

2026-11-24

## 修复者

Claude Sonnet 4.6
