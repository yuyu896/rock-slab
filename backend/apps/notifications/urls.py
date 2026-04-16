from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import NotificationViewSet, ApprovalCCViewSet

router = DefaultRouter()
router.register(r'', NotificationViewSet, basename='notification')
router.register(r'cc', ApprovalCCViewSet, basename='approval-cc')

urlpatterns = [
    path('', include(router.urls)),
]
