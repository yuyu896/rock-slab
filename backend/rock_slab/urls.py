from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from django.db import connection


def health_check(request):
    # 免鉴权维持（容器/deploy 探活依赖）；异常原文不下发（可能含连接目标等
    # 内部信息，account-safety-hardening）——固定响应 + 服务端日志留痕
    import logging
    try:
        connection.ensure_connection()
        return JsonResponse({'status': 'ok'})
    except Exception:
        logging.getLogger('rock_slab.health').exception('health check failed')
        return JsonResponse({'status': 'error'}, status=503)


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/health/', health_check),
    path('api/auth/', include('apps.authentication.urls')),
    path('api/users/', include('apps.users.urls')),
    path('api/permissions/', include('apps.permissions.urls')),
    path('api/regions/', include('apps.organizations.urls_regions')),
    path('api/branches/', include('apps.organizations.urls_branches')),
    path('api/teams/', include('apps.organizations.urls_teams')),
    path('api/departments/', include('apps.organizations.urls_departments')),
    path('api/company/', include('apps.organizations.urls_company')),
    path('api/categories/', include('apps.categories.urls')),
    path('api/suppliers/', include('apps.suppliers.urls')),
    path('api/assets/', include('apps.assets.urls')),
    path('api/transfers/', include('apps.transfers.urls')),
    path('api/inventories/', include('apps.inventories.urls')),
    path('api/reports/', include('apps.reports.urls')),
    path('api/notifications/', include('apps.notifications.urls')),
    path('api/audit/', include('apps.audit.urls')),
]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
