from rest_framework.routers import DefaultRouter
from .views import AssetViewSet, FixedAssetViewSet

router = DefaultRouter(trailing_slash=False)
router.register(r'fixed-assets', FixedAssetViewSet, basename='fixed-asset')
router.register(r'', AssetViewSet, basename='asset')
urlpatterns = router.urls
