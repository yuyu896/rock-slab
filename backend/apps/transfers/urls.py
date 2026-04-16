from rest_framework.routers import DefaultRouter
from .views import TransferViewSet

router = DefaultRouter(trailing_slash=False)
router.register(r'', TransferViewSet, basename='transfer')
urlpatterns = router.urls
