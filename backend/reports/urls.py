
from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import ReportViewSet, TagListView,MyPointsView


router = DefaultRouter()

router.register(
    "",
    ReportViewSet,
    basename="report",
)

urlpatterns = [
    path(
        "tags/",
        TagListView.as_view(),
        name="tag-list",
    ),
    path(
        "points/",
        MyPointsView.as_view(),
        name="points-list",
    ),
]

urlpatterns += router.urls