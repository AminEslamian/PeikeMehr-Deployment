from rest_framework.routers import DefaultRouter

from .views import BlogViewSet


router = DefaultRouter()

router.register(
    "",
    BlogViewSet,
    basename="blog"
)

urlpatterns = router.urls