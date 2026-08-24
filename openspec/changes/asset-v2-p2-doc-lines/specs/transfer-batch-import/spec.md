# transfer-batch-import 增量

## MODIFIED Requirements

### Requirement: 后端批量导入 API
TransferViewSet SHALL 提供 `import_excel` action（POST `/api/transfers/import`），接受 Excel 文件上传，逐行解析并创建流转单。每行 SHALL 生成"1 张单头 + 1 条明细行"（品目按资产编号解析为字典 FK，编号未登记整行拒绝并提示相近编号；采购行单价/总金额、回收行存放位置落入明细行），模板列与分公司校验、编号户籍校验、错误提示格式保持既有契约。导入结果 SHALL 返回 `{ imported: number, errors: string[] }`。

#### Scenario: 批量导入成功
- **WHEN** 用户上传包含多条流转记录的 Excel 文件
- **THEN** 系统逐行创建对应数量的流转单（各含 1 条明细行，默认审批状态为"待审批"），返回成功数量

#### Scenario: 部分行编号未登记
- **WHEN** Excel 中某行的资产编号不在品目字典
- **THEN** 该行导入失败，errors 中包含行号与相近编号建议，其他有效行正常导入
