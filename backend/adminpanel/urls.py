from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
DashboardView,
ReportDashboardView,
ReportDetailView,
SurveyDashboardView,
SurveyCreateView,
SurveyDetailView,
TeacherDashboardView,
TeacherDetailView,
AdminTeacherViewSet,
AdminTagViewSet,
AdminReportViewSet,
AdminReportImageViewSet,
AdminReportVideoViewSet,
AdminMediaViewSet,
AdminPointViewSet,
AdminSurveyViewSet,
AdminQuestionViewSet,
AdminOptionViewSet,
AdminSubmissionViewSet,
AdminAnswerViewSet,
BlogCreateView,
AdminTicketViewSet,
AdminTicketsView
)

app_name = "admin_panel"

router = DefaultRouter()

router.register(
r"teachers",
AdminTeacherViewSet,
basename="admin-teacher",
)

router.register(
r"tags",
AdminTagViewSet,
basename="admin-tag",
)

router.register(
r"reports",
AdminReportViewSet,
basename="admin-report",
)

router.register(
r"report-images",
AdminReportImageViewSet,
basename="admin-report-image",
)

router.register(
r"report-videos",
AdminReportVideoViewSet,
basename="admin-report-video",
)

router.register(
r"media-list",
AdminMediaViewSet,
basename="admin-media",
)

router.register(
r"points",
AdminPointViewSet,
basename="admin-point",
)

router.register(
r"surveys",
AdminSurveyViewSet,
basename="admin-survey",
)

router.register(
r"questions",
AdminQuestionViewSet,
basename="admin-question",
)

router.register(
r"options",
AdminOptionViewSet,
basename="admin-option",
)

router.register(
r"submissions",
AdminSubmissionViewSet,
basename="admin-submission",
)

router.register(
r"answers",
AdminAnswerViewSet,
basename="admin-answer",
)

router.register(
r"tickets",
AdminTicketViewSet,
basename="admin-ticket",
)

urlpatterns = [
path(
"",
DashboardView.as_view(),
name="admin_dashboard",
),
path(
"reports/",
ReportDashboardView.as_view(),
name="ui-reports",
),
path(
"reports/<int:pk>/",
ReportDetailView.as_view(),
name="ui-report-detail",
),
path(
"surveys/",
SurveyDashboardView.as_view(),
name="ui-surveys",
),
path(
"surveys/create/",
SurveyCreateView.as_view(),
name="ui-survey-create",
),
path(
"surveys/<int:pk>/",
SurveyDetailView.as_view(),
name="ui-survey-detail",
),
path(
"teachers/",
TeacherDashboardView.as_view(),
name="ui-teachers",
),
path(
"teachers/<int:pk>/",
TeacherDetailView.as_view(),
name="ui-teacher-detail",
),
path(
"api/",
include(router.urls),
),
path(
"tickets/",
AdminTicketsView.as_view(),
name="ui-tickets"
),
path(
        "blogs/create/",
        BlogCreateView.as_view(),
        name="ui-blog-create"
    ),
]
