## ADDED Requirements

### Requirement: SECRET_KEY 环境变量名统一
系统 SHALL 从环境变量 `SECRET_KEY` 读取 Django 密钥，而非 `DJANGO_SECRET_KEY`。`base.py` 中的 `os.environ.get` 调用 MUST 使用 `SECRET_KEY` 作为键名。

#### Scenario: 生产环境从 .env 文件读取密钥
- **WHEN** `.env` 文件中定义 `SECRET_KEY=abc123` 且 `DJANGO_SETTINGS_MODULE=rock_slab.settings.production`
- **THEN** Django SHALL 成功读取该密钥且不抛出 `ValueError`

#### Scenario: 开发环境使用默认密钥
- **WHEN** 环境变量中未设置 `SECRET_KEY`
- **THEN** 开发环境 SHALL 使用 `dev-insecure-key-change-in-production` 作为默认值，并正常启动

### Requirement: .env.example 与代码一致
`.env.example` 文件中的环境变量名 MUST 与 `settings/base.py` 中的 `os.environ.get` 键名完全匹配。

#### Scenario: 新开发者按 .env.example 配置
- **WHEN** 开发者复制 `.env.example` 为 `.env` 并填写密钥
- **THEN** Django SHALL 成功读取所有配置项，无需额外修改变量名
