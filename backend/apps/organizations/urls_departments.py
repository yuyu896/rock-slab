from rest_framework.routers import DefaultRouter
from .views_departments import DepartmentViewSet

router = DefaultRouter(trailing_slash=False)
router.register(r'', DepartmentViewSet, basename='department')
urlpatterns = router.urls
