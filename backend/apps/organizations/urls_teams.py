from rest_framework.routers import DefaultRouter
from .views import TeamViewSet

router = DefaultRouter(trailing_slash=False)
router.register(r'', TeamViewSet, basename='team')
urlpatterns = router.urls
