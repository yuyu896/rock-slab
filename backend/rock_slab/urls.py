from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from django.db import connection


def health_check(request):
    try:
        connection.ensure_connection()
        return JsonResponse({'status': 'ok'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'detail': str(e)}, status=503)


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/health/', health_check),
    path('api/auth/', include('apps.authentication.urls')),
    path('api/users/', include('apps.users.urls')),
    path('api/regions/', include('apps.organizations.urls_regions')),
    path('api/branches/', include('apps.organizations.urls_branches')),
    path('api/teams/', include('apps.organizations.urls_teams')),
    path('api/categories/', include('apps.categories.urls')),
    path('api/assets/', include('apps.assets.urls')),
    path('api/transfers/', include('apps.transfers.urls')),
    path('api/inventories/', include('apps.inventories.urls')),
    path('api/reports/', include('apps.reports.urls')),
    path('api/notifications/', include('apps.notifications.urls')),
    path('api/audit/', include('apps.audit.urls')),
]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
