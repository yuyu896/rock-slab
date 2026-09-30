#!/usr/bin/env python
import os
import sys


def main():
    # 开发工具：缺省 development 是本地 DX 的刻意选择（shell/migrate 等命令
    # 免设环境变量）。部署入口是 wsgi.py——其缺省 fail-safe 为 production。
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rock_slab.settings.development')
    # Production: set DJANGO_SETTINGS_MODULE=rock_slab.settings.production in .env
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
