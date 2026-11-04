from django.urls import path
from rest_framework.routers import DefaultRouter
from .baseline_views import position_baseline_apply, position_baseline_preview
from .views import (
    ManagementScopeViewSet,
    OperationGrantViewSet,
    effective_permissions,
    operation_catalog,
    my_permissions,
    permission_matrix_organizations,
    position_templates,
    user_authorization,
)

router = DefaultRouter(trailing_slash=False)
router.register(r'management-scopes', ManagementScopeViewSet, basename='management-scope')
router.register(r'operation-grants', OperationGrantViewSet, basename='operation-grant')

urlpatterns = router.urls + [
    path('operations', operation_catalog),
    path('position-templates', position_templates),
    path('position-baselines/preview', position_baseline_preview),
    path('position-baselines/apply', position_baseline_apply),
    path('effective', effective_permissions),
    path('matrix-organizations', permission_matrix_organizations),
    path('me', my_permissions),
    path('users/<uuid:user_id>/authorization', user_authorization),
]
