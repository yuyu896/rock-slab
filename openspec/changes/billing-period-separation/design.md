# 设计文档：账期偏移支持

## 数据模型改动

### ReconciliationTask 模型

```python
# backend/apps/reconciliation/models.py

class ReconciliationTask(UUIDModel, TimestampedModel):
    supplier = models.ForeignKey('suppliers.Supplier', ...)
    period = models.DateField('对账月份')  # 保留：任务导入月份
    billing_period = models.DateField('结算账期')  # 新增：从记账日期提取
    status = models.CharField(...)
    ...
    
    class Meta:
        db_table = 'reconciliation_task'
        ordering = ['-billing_period', 'supplier__name']  # 改为按结算账期排序
        constraints = [
            models.UniqueConstraint(
                fields=['supplier', 'billing_period'],
                name='uniq_recon_supplier_billing_period'
            )
        ]
```

**字段说明**：
- `period`：对账任务月份，记录导入时间，用于列表筛选
- `billing_period`：结算账期，从 Excel"记账日期"列提取的唯一月份，用于金额计算

**唯一约束变更**：
- 旧：`(supplier, period)` → 同供应商同月只能有一个任务
- 新：`(supplier, billing_period)` → 同供应商同结算账期只能有一个任务

## 核心逻辑改动

### 1. Excel 解析（services.py）

```python
def parse_workbook(upload, period):
    # ... 现有解析逻辑 ...
    
    # 提取所有记账日期的唯一月份
    accounting_months = {row['accounting_date'].replace(day=1) for row in parsed}
    
    if len(accounting_months) == 0:
        raise ValidationError({'detail': '订单中没有有效的记账日期'})
    
    if len(accounting_months) > 1:
        raise ValidationError({
            'detail': '订单包含多个结算账期，请拆分为单一账期文件后重新导入',
            'periods': sorted(m.strftime('%Y-%m') for m in accounting_months),
        })
    
    billing_period = accounting_months.pop()
    return parsed, billing_period  # 返回元组
```

**校验规则**：
1. 一个 Excel 文件只能包含同一个结算账期
2. 结算账期从"记账日期"列提取（取年-月）
3. 所有行的记账日期必须属于同一个月份

### 2. 金额计算修正（services.py:153）

```python
# 改前
days, amount = billing_for_period(period, accounting, rent)

# 改后
days, amount = billing_for_period(billing_period, accounting, rent)
```

**影响**：
- `billing_for_period` 的第一个参数从"对账月份"改为"结算账期"
- 保证金额计算按实际结算账期进行

### 3. 导入流程（views.py 或 services.py）

```python
def _prepare_reconciliation_order(supplier_id, period, upload):
    period_date = date.fromisoformat(f'{period}-01')
    supplier = Supplier.objects.filter(pk=supplier_id).first()
    if supplier is None:
        raise ValidationError({'supplier': '供应商不存在'})
    
    parsed, billing_period = parse_workbook(upload, period_date)  # 解包
    
    # 检查唯一约束
    existing = ReconciliationTask.objects.filter(
        supplier=supplier, 
        billing_period=billing_period
    ).first()
    
    if existing:
        raise ValidationError({
            'detail': f'供应商 {supplier.name} 的 {billing_period.strftime("%Y-%m")} 账期已存在对账任务',
            'existingTaskId': str(existing.id),
        })
    
    return supplier, period_date, billing_period, parsed
```

### 4. 重新对账（rematch）

```python
def rematch_task(task_id):
    task = ReconciliationTask.objects.get(pk=task_id)
    # billing_period 不变，从现有订单行重新比对
    # build_comparison 中使用 task.billing_period
```

## 数据迁移

### 迁移脚本

```python
# migrations/xxxx_add_billing_period.py

from django.db import migrations, models

def forwards(apps, schema_editor):
    """从现有订单行提取 billing_period"""
    Task = apps.get_model('reconciliation', 'ReconciliationTask')
    OrderRow = apps.get_model('reconciliation', 'ReconciliationOrderRow')
    
    for task in Task.objects.all():
        # 从最早版本的第一行提取记账日期
        first_row = (
            OrderRow.objects
            .filter(version__task=task)
            .order_by('version__version_number', 'row_number')
            .first()
        )
        
        if first_row and first_row.accounting_date:
            task.billing_period = first_row.accounting_date.replace(day=1)
        else:
            # fallback：假设对账月份 = 结算账期
            task.billing_period = task.period
        
        task.save(update_fields=['billing_period'])

class Migration(migrations.Migration):
    dependencies = [
        ('reconciliation', 'xxxx_previous_migration'),
    ]
    
    operations = [
        migrations.AddField(
            model_name='reconciliationtask',
            name='billing_period',
            field=models.DateField('结算账期', null=True),
        ),
        migrations.RunPython(forwards, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='reconciliationtask',
            name='billing_period',
            field=models.DateField('结算账期'),
        ),
        migrations.RemoveConstraint(
            model_name='reconciliationtask',
            name='uniq_recon_supplier_period',
        ),
        migrations.AddConstraint(
            model_name='reconciliationtask',
            constraint=models.UniqueConstraint(
                fields=['supplier', 'billing_period'],
                name='uniq_recon_supplier_billing_period'
            ),
        ),
    ]
```

## 前端改动

### API 类型定义

```typescript
// frontend/src/api/reconciliation.ts

export interface ReconciliationTask {
  id: string
  supplierId: string
  supplierName: string
  period: string              // 对账月份 YYYY-MM
  billingPeriod: string       // 结算账期 YYYY-MM（新增）
  status: 'draft' | 'archived'
  ...
}

export interface ReconciliationImportPreview {
  supplierId: string
  supplierName: string
  period: string              // 对账月份
  billingPeriod: string       // 结算账期（新增）
  ...
}
```

### 列表页筛选器

```vue
<!-- ReconciliationOrders.vue -->
<el-form-item label="对账月份">
  <el-date-picker 
    v-model="filters.period" 
    type="month"
    placeholder="选择月份"
  />
</el-form-item>

<el-form-item label="结算账期">
  <el-date-picker 
    v-model="filters.billingPeriod" 
    type="month"
    placeholder="选择账期"
  />
</el-form-item>
```

### 详情页 Banner

```vue
<!-- ReconciliationDifferences.vue -->
<el-descriptions :column="3" border>
  <el-descriptions-item label="供应商">
    {{ task.supplierName }}
  </el-descriptions-item>
  <el-descriptions-item label="对账月份">
    {{ task.period }}
  </el-descriptions-item>
  <el-descriptions-item label="结算账期">
    {{ task.billingPeriod }}
  </el-descriptions-item>
  <el-descriptions-item label="版本号">
    v{{ task.currentVersion }}
  </el-descriptions-item>
</el-descriptions>
```

## 影响范围总结

| 模块 | 文件 | 改动类型 |
|------|------|---------|
| 后端模型 | `models.py` | 新增字段、改唯一约束 |
| 后端服务 | `services.py` | 解析返回值、金额计算参数 |
| 后端视图 | `views.py` | 导入流程、唯一约束检查 |
| 数据迁移 | `migrations/` | 新增迁移脚本 |
| 前端类型 | `api/reconciliation.ts` | 新增字段类型 |
| 前端列表 | `ReconciliationOrders.vue` | 筛选器、表格列 |
| 前端详情 | `ReconciliationDifferences.vue` | Banner 信息 |
| 前端付款 | `ReconciliationPayment.vue` | 标题显示 |

## 兼容性

- **向后兼容**：存量数据通过迁移补全 `billing_period`
- **API 兼容**：前端必须同步更新（新增 `billingPeriod` 字段）
- **部署顺序**：先部署后端（迁移），再部署前端
