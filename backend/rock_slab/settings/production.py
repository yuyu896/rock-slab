from .base import *  # noqa: F401,F403
import dj_database_url

# -------------------------------------------------------------------------
# Security
# -------------------------------------------------------------------------
DEBUG = False

SECRET_KEY = os.environ.get('SECRET_KEY')  # noqa: F405
if not SECRET_KEY:
    raise ValueError("SECRET_KEY environment variable is required in production")

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'qhpanpan.top,www.qhpanpan.top').split(',')  # noqa: F405

# CSRF trusted origins（前端 SPA 提交表单时需要；也覆盖 Django admin 会话认证）
CSRF_TRUSTED_ORIGINS = os.environ.get(
    'CSRF_TRUSTED_ORIGINS',
    'https://qhpanpan.top,https://www.qhpanpan.top',
).split(',')  # noqa: F405

# HTTPS / SSL —— Nginx 已处理 HTTP→HTTPS 重定向，Django 层默认关闭，避免健康检查被 301 卡住
SECURE_SSL_REDIRECT = os.environ.get('SECURE_SSL_REDIRECT', 'False') == 'True'  # noqa: F405
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# -------------------------------------------------------------------------
# Database
# -------------------------------------------------------------------------
DATABASE_URL = os.environ.get('DATABASE_URL')  # noqa: F405
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is required in production")

DATABASES = {
    'default': dj_database_url.parse(DATABASE_URL, conn_max_age=600, conn_health_checks=True)
}

# -------------------------------------------------------------------------
# Cache (Redis)
# -------------------------------------------------------------------------
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': os.environ.get('REDIS_URL', 'redis://localhost:6379/1'),  # noqa: F405
        'KEY_PREFIX': 'rock_slab',
        'TIMEOUT': 300,
    }
}

# -------------------------------------------------------------------------
# CORS
# -------------------------------------------------------------------------
CORS_ALLOWED_ORIGINS = [
    'https://qhpanpan.top',
    'https://www.qhpanpan.top',
]
CORS_ALLOW_CREDENTIALS = True

# -------------------------------------------------------------------------
# Static & Media files
# -------------------------------------------------------------------------
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'  # noqa: F405

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'  # noqa: F405

# 上传体积上限（与 nginx client_max_body_size 对齐，容纳资产导入模板等大文件；
# Django 默认仅 2.5MB，会拦截合法的大体积导入）
DATA_UPLOAD_MAX_MEMORY_SIZE = 60 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 60 * 1024 * 1024

# -------------------------------------------------------------------------
# Logging
# -------------------------------------------------------------------------
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{asctime}] {levelname} {name} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
