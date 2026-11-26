# 资产管理方式切换为消耗品 - 执行说明

## 概述

将以下7个资产的管理方式从"数量管理"切换为"消耗品"：

| 资产编号 | 资产名称 | 生产状态 | 台账记录 | 总库存 |
|---------|---------|---------|---------|--------|
| A-c00030 | 地毯 | 数量管理 | 6条 | 23个 |
| A-c00049 | 玻璃罐 | 数量管理 | 2条 | 51个 |
| A-c00072 | 桌面支架 | 数量管理 | 3条 | 15个 |
| B-b00033 | 白板笔 | 数量管理 | 57条 | 1869个 |
| B-b00077 | 缠绕绳 | 数量管理 | 0条 | 0个 |
| B-b00089 | 不干胶A4纸 | 数量管理 | 15条 | 870个 |
| B-d00029 | 支架 | 数量管理 | 12条 | 40个 |

## 本地测试结果 ✅

已在本地环境完成测试：
- ✅ 模拟运行成功
- ✅ 实际执行成功（6个资产，B-b00089本地不存在）
- ✅ 验证切换结果正确
- ✅ 无实例记录阻止
- ✅ 事务回滚机制正常

## 生产执行步骤

### 准备工作

1. 连接到生产服务器：
```bash
ssh root@47.97.43.28
```

2. 上传执行脚本：
```bash
# 从本地上传
scp backend/switch_to_consumable_prod.py root@47.97.43.28:/tmp/
```

或者在服务器上直接创建：
```bash
# 在服务器上
cat > /tmp/switch_to_consumable_prod.py << 'EOF'
# (复制 switch_to_consumable_prod.py 的完整内容)
EOF
```

### 执行流程

#### 第一步：模拟运行（必须）

```bash
docker exec rock-slab-backend python /tmp/switch_to_consumable_prod.py --dry-run
```

**预期输出**：
- 显示每个资产的当前状态
- 显示是否有实例记录阻止切换
- 显示台账情况
- 最后显示"模拟运行完成，所有更改已回滚"

**检查点**：
- [ ] 7个资产都找到了
- [ ] 无实例记录阻止
- [ ] 无错误信息
- [ ] 成功数量为7

#### 第二步：实际执行

确认模拟运行无误后：

```bash
docker exec rock-slab-backend python /tmp/switch_to_consumable_prod.py --apply
```

脚本会要求二次确认：
1. 显示将要修改的资产列表
2. 提示 "按 Ctrl+C 取消，按回车继续..."
3. 按回车继续执行

**预期输出**：
- 每个资产显示"✅ 已切换: 数量管理 → 消耗品"
- 最后显示"✅ 实际执行完成，更改已提交到数据库"
- 退出码为 0

#### 第三步：验证结果

```bash
docker exec rock-slab-backend python manage.py shell << 'EOF'
from apps.categories.models import Category
codes = ["A-c00030", "A-c00049", "A-c00072", "B-b00033", "B-b00077", "B-b00089", "B-d00029"]
print("验证切换结果：")
for code in codes:
    c = Category.objects.get(asset_code=code)
    print(f"{code}: {c.asset_name} - {c.get_management_type_display()}")
EOF
```

**预期输出**：所有资产的管理方式都显示为"消耗品"

## 风险评估

### 低风险 ✅
- **无实例记录**：所有资产都没有实例，不会触发阻止逻辑
- **仅更改元数据**：只修改 `management_type` 字段，不涉及台账数据
- **事务保护**：使用 Django 事务，失败自动回滚
- **已本地测试**：逻辑已在本地环境验证通过

### 影响范围
- **直接影响**：资产类目的 `management_type` 字段
- **间接影响**：
  - 前端可能根据管理方式显示不同的操作选项
  - 流转单据可能需要区分消耗品的处理逻辑
  - 台账数据保持不变，仅管理方式标签变化

### 回滚方案

如需回滚，执行以下 SQL（在数据库容器中）：

```sql
-- 备份当前状态
CREATE TABLE categories_category_backup_20261117 AS
SELECT * FROM categories_category
WHERE asset_code IN ('A-c00030', 'A-c00049', 'A-c00072', 'B-b00033', 'B-b00077', 'B-b00089', 'B-d00029');

-- 回滚管理方式
UPDATE categories_category
SET management_type = 'quantity'
WHERE asset_code IN ('A-c00030', 'A-c00049', 'A-c00072', 'B-b00033', 'B-b00077', 'B-b00089', 'B-d00029')
  AND management_type = 'consumable';
```

## 注意事项

1. **执行时机**：建议在业务低峰期执行（如深夜或周末）
2. **备份确认**：虽然风险低，但建议执行前确认有最新数据库备份
3. **监控观察**：执行后观察前端相关功能是否正常
4. **日志记录**：保存执行输出日志，便于审计追溯

## 清理

执行完成并验证无误后，删除临时脚本：

```bash
rm /tmp/switch_to_consumable_prod.py
```

## 时间估算

- 模拟运行：< 5秒
- 实际执行：< 5秒
- 验证结果：< 5秒
- **总计**：< 15秒

## 联系信息

如有问题，请联系系统管理员。

---

**执行记录**：

- [ ] 本地测试完成：2026-11-17
- [ ] 生产模拟运行完成：______
- [ ] 生产实际执行完成：______
- [ ] 结果验证完成：______
- [ ] 业务功能确认正常：______
