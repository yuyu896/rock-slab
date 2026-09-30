## ADDED Requirements

### Requirement: 头像维护单端点方法分流

头像上传（POST）与删除（DELETE）MUST 共用单一 action 端点按请求方法内部分流，MUST NOT 以相同 `url_path` 声明两个 action（DRF 路由按方法名排序注册、先注册者的 pattern 遮蔽后者，致 POST 405）。两种方法 MUST 维持既有权限口径（登录 + 本人或管理员）与校验（类型/大小）。

#### Scenario: 上传头像成功

- **WHEN** 用户对自己的账号 POST 合法图片（JPG/PNG/WebP ≤2MB）
- **THEN** 头像更新成功（200/响应含新头像），不再 405

#### Scenario: 删除头像成功

- **WHEN** 用户 DELETE 自己的头像
- **THEN** 自定义头像清除并返回用户资料
