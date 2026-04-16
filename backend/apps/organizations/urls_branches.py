from rest_framework.routers import DefaultRouter
from .views import BranchViewSet

router = DefaultRouter(trailing_slash=False)
router.register(r'', BranchViewSet, basename='branch')
urlpatterns = router.urls
