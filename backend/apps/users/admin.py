# 用户模型不注册 Django Admin（p3-backend-hardening）：
# admin 表单是 API 之外的旁路写入口——直写 password 列无校验、停用不联动
# is_active、不清理 token，绕过权线闸与审计。用户管理唯一入口为 /api/users/
# （全套闸门）；运维需直接修用户数据时走 manage.py shell（会话留痕）。
from django.contrib import admin  # noqa: F401  # admin 站点本身保留（其余模型排障用）
