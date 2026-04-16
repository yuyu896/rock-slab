## 手机号格式校验 — 技术设计

### 1. 后端校验

#### 1.1 Serializer 层验证

文件：`apps/users/serializers.py`

在 `UserSerializer` 的 `phone` 字段上增加 `RegexValidator`：

```python
from django.core.validators import RegexValidator

phone_validator = RegexValidator(
    regex=r'^\d{11}$',
    message='手机号必须为11位数字',
)

class UserSerializer(serializers.ModelSerializer):
    phone = serializers.CharField(
        validators=[phone_validator],
        ...
    )
```

选择在 Serializer 而非 Model 层加验证器的原因：
- Model 的 `phone` 字段同时用于 `USERNAME_FIELD`，在 manager 的 `create_user` 中也会赋值，但 manager 层不适合处理 HTTP 错误信息
- Serializer 是 DRF API 的入口，在此验证可以直接返回 400 错误和友好提示
- `RegexValidator` 在 `create()` 和 `update()` 时均自动触发

#### 1.2 登录接口

文件：`apps/users/authentication.py`（`PhoneModelBackend`）

在 `authenticate()` 方法入口增加格式前置校验：

```python
def authenticate(self, request, phone=None, password=None, **kwargs):
    if not phone or not re.match(r'^\d{11}$', phone):
        return None
    ...
```

不返回报错信息，仅返回 None 让 DRF 返回标准的"无法使用提供的凭据登录"。

### 2. 前端校验

#### 2.1 用户管理表单

文件：`frontend/src/views/Organization.vue`

用户编辑表单的手机号 `<input>` 增加：
- `maxlength="11"` 限制最大输入长度
- `type="tel"` 触发移动端数字键盘
- 提交前校验：`/^\d{11}$/.test(phone)` 不通过则提示"手机号必须为11位数字"并阻止提交

#### 2.2 登录表单

文件：`frontend/src/views/Login.vue`

登录表单的手机号 `<input>` 同样增加 `maxlength="11"` 和提交前校验。

### 3. 不做的事

- **不做手机号号段校验**（如 13x/15x/18x 开头）：号段随时在增加，维护成本高且无业务必要性
- **不迁移已有数据**：历史数据中非 11 位手机号的用户不受影响，仅在创建/更新时校验
- **不改 Model 字段定义**：`max_length=20` 保持不变，避免数据库迁移
