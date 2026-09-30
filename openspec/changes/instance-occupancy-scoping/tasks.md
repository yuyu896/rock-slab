## 1. 实现

- [x] 1.1 `backend/apps/transfers/views.py` 的 `instance_occupancy`：branch 名解析 Branch（`filter(name=…).first()`）；可解析则 `validate_branches_in_scope(request.user, branch.id)`（admin/全部数据豁免、越界 400）；不可解析或缺参维持 `[]`；查询条件由 `branch__name=` 收敛为 `branch=`

## 2. 测试

- [x] 2.1 `backend/tests/test_instance_occupancy.py` 新增 5 例：本分公司 200、他分公司 400（含授权范围提示）、未知分公司 200 空列表、admin 他分公司 200、全部数据授权他分公司 200
- [x] 2.2 全量 `pytest` 通过（880 passed / 5 skipped / 6 xfailed）

## 3. 收尾

- [ ] 3.1 手验要点记录（建单点选器占用标注正常；跨范围试探得 400 提示）

> 手验要点：以本分公司账号建领用/调拨单，点选实例时占用标注正常显示；用接口工具以他分公司名请求 /api/transfers/instance-occupancy 应得 400「您只能操作授权范围内的分公司」。
