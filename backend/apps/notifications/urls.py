from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import NotificationViewSet, ApprovalCCViewSet

router = DefaultRouter()
router.register(r'', NotificationViewSet, basename='notification')

# ApprovalCC is registered with explicit paths to avoid the NotificationViewSet
# detail pattern ^(?P<pk>[^/.]+)/$ capturing "cc" as a pk value.
cc_list = ApprovalCCViewSet.as_view({'get': 'list'})
cc_detail = ApprovalCCViewSet.as_view({'get': 'retrieve'})
cc_mark_read = ApprovalCCViewSet.as_view({'post': 'mark_read'})
cc_mark_all_read = ApprovalCCViewSet.as_view({'post': 'mark_all_read'})

urlpatterns = [
    path('cc/', cc_list, name='approval-cc-list'),
    path('cc/mark_all_read/', cc_mark_all_read, name='approval-cc-mark-all-read'),
    path('cc/<uuid:pk>/', cc_detail, name='approval-cc-detail'),
    path('cc/<uuid:pk>/mark_read/', cc_mark_read, name='approval-cc-mark-read'),
    path('', include(router.urls)),
]
