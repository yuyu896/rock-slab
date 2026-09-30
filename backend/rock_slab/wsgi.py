import os

from django.core.wsgi import get_wsgi_application

# WSGI 是部署入口：漏设环境变量时 fail-safe 到生产配置（compose 仍显式注入，
# 双保险）。开发用 manage.py（其缺省为 development），两者分工见 manage.py 注释。
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rock_slab.settings.production')

application = get_wsgi_application()
