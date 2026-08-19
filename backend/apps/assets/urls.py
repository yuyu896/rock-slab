from rest_framework.routers import DefaultRouter
from .views import AssetViewSet, AssetStockViewSet, FixedAssetViewSet

router = DefaultRouter(trailing_slash=False)
# summary 前缀必须注册在 r'' 之前，否则会被 AssetViewSet 的通配路由吞掉
router.register(r'summary', AssetStockViewSet, basename='asset-stock')
router.register(r'fixed-assets', FixedAssetViewSet, basename='fixed-asset')
router.register(r'', AssetViewSet, basename='asset')
urlpatterns = router.urls
