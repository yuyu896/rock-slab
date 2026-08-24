from rest_framework.routers import DefaultRouter
from .views import AssetStockViewSet, FixedAssetViewSet, LedgerAdjustmentViewSet

router = DefaultRouter(trailing_slash=False)
# 台账 / 调整单 / 实例档案（Asset 主路由已随 P2 第三刀退役）
router.register(r'summary', AssetStockViewSet, basename='asset-stock')
router.register(r'adjustments', LedgerAdjustmentViewSet, basename='ledger-adjustment')
router.register(r'fixed-assets', FixedAssetViewSet, basename='fixed-asset')
urlpatterns = router.urls
