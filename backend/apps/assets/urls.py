from rest_framework.routers import DefaultRouter
from .views import AssetViewSet

router = DefaultRouter(trailing_slash=False)
router.register(r'', AssetViewSet, basename='asset')
urlpatterns = router.urls
