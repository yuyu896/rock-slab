## 1. 后端序列化器必填校验

- [ ] 1.1 `TransferActionSerializer`：`调出分公司` 改 `required=True`（不再 allow_blank）
- [ ] 1.2 `FixedAssetSerializer.validate`：加分公司/资产名称/序列号非空校验
- [ ] 1.3 `AssetSerializer`：确认分公司/编号/名称已有约束（模型非 blank）
- [ ] 1.4 测试

## 2. 前端表单校验确认

- [ ] 2.1 检查各 Create 表单前端必填校验是否与后端一致
- [ ] 2.2 补齐缺失的前端校验（如有）

## 3. 验证

- [ ] 3.1 pytest + vue-tsc
