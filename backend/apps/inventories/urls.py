from rest_framework.routers import DefaultRouter
from .views import InventoryTaskViewSet

router = DefaultRouter(trailing_slash=False)
router.register(r'', InventoryTaskViewSet, basename='inventory')
urlpatterns = router.urls
