from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import (
    ManagementScopeViewSet,
    OperationGrantViewSet,
    effective_permissions,
    operation_catalog,
    my_permissions,
    position_templates,
)

router = DefaultRouter(trailing_slash=False)
router.register(r'management-scopes', ManagementScopeViewSet, basename='management-scope')
router.register(r'operation-grants', OperationGrantViewSet, basename='operation-grant')

urlpatterns = router.urls + [
    path('operations', operation_catalog),
    path('position-templates', position_templates),
    path('effective', effective_permissions),
    path('me', my_permissions),
]
