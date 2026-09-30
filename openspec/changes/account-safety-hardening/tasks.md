## 1. 实现

- [x] 1.1 users/views.py 头像 upload/delete 合并为单 action 方法分流；serializers.py phone 加 UniqueValidator（中文 message）
- [x] 1.2 account_lockout.py 计数改 cache.incr + ValueError 初始化（注释记录固定窗语义）
- [x] 1.3 audit/decorators.py is_success：Response 且 status>=400 → False
- [x] 1.4 rock_slab/urls.py health 异常分支固定响应 + logger.exception

## 2. 测试

- [x] 2.1 头像 POST 5 个 xfail 转正；重复手机号 xfail 转正；新增 is_success(400/200)、health 异常、计数原子用例
- [x] 2.2 全量 `pytest` 通过

## 3. 收尾

- [ ] 3.1 手验要点（头像上传/删除、撞号 400、审计失败态、health）

> 实施备注：头像越权用例按实际语义断言 404（范围外目标经 get_object 隐藏存在性，先于 403 校验）。手验：个人资料上传/删除头像正常；建重复手机号 → 400「该手机号已被注册」；改密输错旧密码后审计日志 is_success=失败；curl /api/health/ 正常 200。
