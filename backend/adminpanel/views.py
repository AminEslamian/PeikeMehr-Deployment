from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.contrib.auth.mixins import UserPassesTestMixin, LoginRequiredMixin
from django.views.generic import TemplateView

from rest_framework import permissions, viewsets, filters, status
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import (
    OpenApiParameter,
    extend_schema,
    extend_schema_view,
)

from accounts.models import Teacher
from reports.models import Point, Report, ReportImage, ReportVideo, Tag
from survey.models import Survey, Question, Option, Submission, Answer
from tickets.models import Ticket

from .serializers import (
    AdminTeacherSerializer,
    AdminTagSerializer,
    AdminReportSerializer,
    AdminReportImageSerializer,
    AdminReportVideoSerializer,
    AdminPointSerializer,
    AdminSurveySerializer,
    AdminQuestionSerializer,
    AdminOptionSerializer,
    AdminSubmissionSerializer,
    AdminAnswerSerializer,
    AdminReportWithMediaSerializer,
    AdminTicketSerializer
)


# ==========================================
# کلاس پجینیشن اختصاصی (Pagination Class)
# ==========================================
class StandardResultsSetPagination(PageNumberPagination):
    page_size = 5  # تعداد آیتم‌ها در هر صفحه به صورت پیش‌فرض
    page_size_query_param = 'page_size'  # امکان تغییر تعداد در درخواست (مثلا ?page_size=20)
    max_page_size = 100  # سقف مجاز آیتم‌ها در یک صفحه



# ==========================================
# Template Views
# ==========================================
class StaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Only staff/superusers may open the legacy admin shell pages."""

    def test_func(self):
        user = self.request.user
        return bool(
            user.is_authenticated
            and (user.is_staff or user.is_superuser)
        )

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            raise PermissionDenied
        return super().handle_no_permission()


class DashboardView(StaffRequiredMixin, TemplateView):
    template_name = "admin_panel/dashboard.html"


class AdminTicketsView(StaffRequiredMixin, TemplateView):
    template_name = "admin_panel/tickets.html"


class BlogCreateView(StaffRequiredMixin, TemplateView):
    template_name = "admin_panel/blog_create.html"


class ReportDashboardView(StaffRequiredMixin, TemplateView):
    template_name = "admin_panel/reports.html"


class ReportDetailView(StaffRequiredMixin, TemplateView):
    template_name = "admin_panel/report_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["report_id"] = kwargs.get("pk")
        return context


class SurveyDashboardView(StaffRequiredMixin, TemplateView):
    template_name = "admin_panel/surveys.html"


class SurveyCreateView(StaffRequiredMixin, TemplateView):
    template_name = "admin_panel/survey_form.html"


class SurveyDetailView(StaffRequiredMixin, TemplateView):
    template_name = "admin_panel/survey_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["survey_id"] = kwargs.get("pk")
        return context


class TeacherDashboardView(StaffRequiredMixin, TemplateView):
    template_name = "admin_panel/teachers.html"


class TeacherDetailView(StaffRequiredMixin, TemplateView):
    template_name = "admin_panel/teacher_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["teacher_id"] = kwargs.get("pk")
        return context


# ==========================================
# API ViewSets (همراه با Pagination)
# ==========================================
@extend_schema_view(
    list=extend_schema(tags=["Admin Teachers"], summary="لیست معلمان"),
    retrieve=extend_schema(tags=["Admin Teachers"], summary="جزئیات معلم"),
    create=extend_schema(tags=["Admin Teachers"], summary="ایجاد معلم"),
    update=extend_schema(tags=["Admin Teachers"], summary="به‌روزرسانی کامل معلم"),
    partial_update=extend_schema(tags=["Admin Teachers"], summary="به‌روزرسانی جزئی معلم"),
    destroy=extend_schema(tags=["Admin Teachers"], summary="حذف معلم"),
)
class AdminTeacherViewSet(viewsets.ModelViewSet):
    # Staff and superuser accounts are operators, not educators. They must
    # not appear in the teacher list or be editable through this endpoint.
    queryset = (
        Teacher.objects
        .filter(is_staff=False, is_superuser=False)
        .order_by("-id")
    )
    serializer_class = AdminTeacherSerializer
    permission_classes = [permissions.IsAdminUser]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["province", "city", "position"]
    search_fields = ["first_name", "last_name", "phone_number", "national_id"]


@extend_schema_view(
    list=extend_schema(tags=["Admin Tags"], summary="لیست تگ‌ها"),
    retrieve=extend_schema(tags=["Admin Tags"], summary="جزئیات تگ"),
    create=extend_schema(tags=["Admin Tags"], summary="ایجاد تگ"),
    update=extend_schema(tags=["Admin Tags"], summary="به‌روزرسانی کامل تگ"),
    partial_update=extend_schema(tags=["Admin Tags"], summary="به‌روزرسانی جزئی تگ"),
    destroy=extend_schema(tags=["Admin Tags"], summary="حذف تگ"),
)
class AdminTagViewSet(viewsets.ModelViewSet):
    queryset = Tag.objects.all().order_by("name")
    serializer_class = AdminTagSerializer
    permission_classes = [permissions.IsAdminUser]
    filter_backends = [filters.SearchFilter]
    search_fields = ["name"]


@extend_schema_view(
    list=extend_schema(tags=["Admin Reports"], summary="لیست گزارش‌ها"),
    retrieve=extend_schema(tags=["Admin Reports"], summary="جزئیات گزارش"),
    create=extend_schema(tags=["Admin Reports"], summary="ایجاد گزارش"),
    update=extend_schema(tags=["Admin Reports"], summary="به‌روزرسانی کامل گزارش"),
    partial_update=extend_schema(tags=["Admin Reports"], summary="به‌روزرسانی جزئی گزارش"),
    destroy=extend_schema(tags=["Admin Reports"], summary="حذف گزارش"),
)
class AdminReportViewSet(viewsets.ModelViewSet):
    queryset = (
        Report.objects
        .select_related("teacher")
        .prefetch_related("tags", "images", "videos")
        .all()
        .order_by("-created_at")
    )
    serializer_class = AdminReportSerializer
    permission_classes = [permissions.IsAdminUser]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ["teacher", "teacher__province", "teacher__city"]
    search_fields = [
        "text",
        "teacher__first_name",
        "teacher__last_name",
        "teacher__phone_number",
    ]


@extend_schema_view(
    list=extend_schema(tags=["Admin Media"], summary="لیست تصاویر گزارش"),
    retrieve=extend_schema(tags=["Admin Media"], summary="جزئیات تصویر"),
    create=extend_schema(tags=["Admin Media"], summary="ایجاد تصویر"),
    update=extend_schema(tags=["Admin Media"], summary="به‌روزرسانی کامل تصویر"),
    partial_update=extend_schema(tags=["Admin Media"], summary="به‌روزرسانی جزئی تصویر"),
    destroy=extend_schema(tags=["Admin Media"], summary="حذف تصویر"),
)
class AdminReportImageViewSet(viewsets.ModelViewSet):
    queryset = (
        ReportImage.objects
        .select_related("report", "report__teacher")
        .prefetch_related("report__tags")
        .all()
        .order_by("-created_at")
    )
    serializer_class = AdminReportImageSerializer
    permission_classes = [permissions.IsAdminUser]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = [
        "report",
        "report__teacher",
        "report__teacher__province",
        "report__teacher__city",
    ]
    search_fields = [
        "report__text",
        "report__teacher__first_name",
        "report__teacher__last_name",
        "report__teacher__phone_number",
    ]


@extend_schema_view(
    list=extend_schema(tags=["Admin Media"], summary="لیست ویدیوهای گزارش"),
    retrieve=extend_schema(tags=["Admin Media"], summary="جزئیات ویدیو"),
    create=extend_schema(tags=["Admin Media"], summary="ایجاد ویدیو"),
    update=extend_schema(tags=["Admin Media"], summary="به‌روزرسانی کامل ویدیو"),
    partial_update=extend_schema(tags=["Admin Media"], summary="به‌روزرسانی جزئی ویدیو"),
    destroy=extend_schema(tags=["Admin Media"], summary="حذف ویدیو"),
)
class AdminReportVideoViewSet(viewsets.ModelViewSet):
    queryset = (
        ReportVideo.objects
        .select_related("report", "report__teacher")
        .prefetch_related("report__tags")
        .all()
        .order_by("-created_at")
    )
    serializer_class = AdminReportVideoSerializer
    permission_classes = [permissions.IsAdminUser]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = [
        "report",
        "report__teacher",
        "report__teacher__province",
        "report__teacher__city",
    ]
    search_fields = [
        "report__text",
        "report__teacher__first_name",
        "report__teacher__last_name",
        "report__teacher__phone_number",
    ]


from django.db.models import Q
from rest_framework import viewsets, permissions
from rest_framework.response import Response

class AdminMediaViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAdminUser]
    pagination_class = StandardResultsSetPagination
    serializer_class = AdminReportWithMediaSerializer

    @extend_schema(
        tags=["Admin Media"],
        summary="لیست تجمیعی رسانه‌های گزارش‌ها",
        parameters=[
            OpenApiParameter("media_type", str, OpenApiParameter.QUERY, enum=["image", "video"]),
            OpenApiParameter("province", str, OpenApiParameter.QUERY),
            OpenApiParameter("city", str, OpenApiParameter.QUERY),
            OpenApiParameter("teacher", int, OpenApiParameter.QUERY),
            OpenApiParameter("search", str, OpenApiParameter.QUERY),
            OpenApiParameter("all", bool, OpenApiParameter.QUERY, description="بدون پجینیشن"),
            OpenApiParameter("page", int, OpenApiParameter.QUERY),
            OpenApiParameter("page_size", int, OpenApiParameter.QUERY),
        ],
        responses={200: AdminReportWithMediaSerializer(many=True)},
    )
    def list(self, request):
        params = request.query_params
        media_type = params.get("media_type")

        queryset = (
            Report.objects
            .select_related("teacher")
            .prefetch_related("images", "videos", "tags")
        )

        if params.get("province"):
            queryset = queryset.filter(
                teacher__province=params.get("province")
            )

        if params.get("city"):
            queryset = queryset.filter(
                teacher__city=params.get("city")
            )

        if params.get("teacher"):
            queryset = queryset.filter(
                teacher_id=params.get("teacher")
            )

        if params.get("search"):
            search = params.get("search")

            queryset = queryset.filter(
                Q(teacher__first_name__icontains=search) |
                Q(teacher__last_name__icontains=search) |
                Q(text__icontains=search)
            )

        queryset = queryset.distinct().order_by("-created_at")

        # بدون pagination
        if params.get("all"):
            data = AdminReportWithMediaSerializer(
                queryset,
                many=True,
                context={"request": request}
            ).data

            if media_type == "image":
                for item in data:
                    item.pop("videos", None)

            elif media_type == "video":
                for item in data:
                    item.pop("images", None)

            return Response(data)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)

        data = AdminReportWithMediaSerializer(
            page,
            many=True,
            context={"request": request}
        ).data

        if media_type == "image":
            for item in data:
                item.pop("videos", None)

        elif media_type == "video":
            for item in data:
                item.pop("images", None)

        return paginator.get_paginated_response(data)


@extend_schema_view(
    list=extend_schema(tags=["Admin Points"], summary="لیست امتیازها"),
    retrieve=extend_schema(tags=["Admin Points"], summary="جزئیات امتیاز"),
    create=extend_schema(tags=["Admin Points"], summary="ایجاد امتیاز"),
    update=extend_schema(tags=["Admin Points"], summary="به‌روزرسانی کامل امتیاز"),
    partial_update=extend_schema(tags=["Admin Points"], summary="به‌روزرسانی جزئی امتیاز"),
    destroy=extend_schema(tags=["Admin Points"], summary="حذف امتیاز"),
)
class AdminPointViewSet(viewsets.ModelViewSet):
    queryset = Point.objects.select_related("teacher").all().order_by("-created_at")
    serializer_class = AdminPointSerializer
    permission_classes = [permissions.IsAdminUser]


@extend_schema_view(
    list=extend_schema(tags=["Admin Surveys"], summary="لیست نظرسنجی‌ها"),
    retrieve=extend_schema(tags=["Admin Surveys"], summary="جزئیات نظرسنجی"),
    create=extend_schema(tags=["Admin Surveys"], summary="ایجاد نظرسنجی"),
    update=extend_schema(tags=["Admin Surveys"], summary="به‌روزرسانی کامل نظرسنجی"),
    partial_update=extend_schema(tags=["Admin Surveys"], summary="به‌روزرسانی جزئی نظرسنجی"),
    destroy=extend_schema(tags=["Admin Surveys"], summary="حذف نظرسنجی"),
)
class AdminSurveyViewSet(viewsets.ModelViewSet):
    queryset = Survey.objects.all().order_by("-id")
    serializer_class = AdminSurveySerializer
    permission_classes = [permissions.IsAdminUser]


@extend_schema_view(
    list=extend_schema(tags=["Admin Surveys"], summary="لیست سوال‌ها"),
    retrieve=extend_schema(tags=["Admin Surveys"], summary="جزئیات سوال"),
    create=extend_schema(tags=["Admin Surveys"], summary="ایجاد سوال"),
    update=extend_schema(tags=["Admin Surveys"], summary="به‌روزرسانی کامل سوال"),
    partial_update=extend_schema(tags=["Admin Surveys"], summary="به‌روزرسانی جزئی سوال"),
    destroy=extend_schema(tags=["Admin Surveys"], summary="حذف سوال"),
)
class AdminQuestionViewSet(viewsets.ModelViewSet):
    queryset = Question.objects.all().order_by("order")
    serializer_class = AdminQuestionSerializer
    permission_classes = [permissions.IsAdminUser]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["survey"]


@extend_schema_view(
    list=extend_schema(tags=["Admin Surveys"], summary="لیست گزینه‌ها"),
    retrieve=extend_schema(tags=["Admin Surveys"], summary="جزئیات گزینه"),
    create=extend_schema(tags=["Admin Surveys"], summary="ایجاد گزینه"),
    update=extend_schema(tags=["Admin Surveys"], summary="به‌روزرسانی کامل گزینه"),
    partial_update=extend_schema(tags=["Admin Surveys"], summary="به‌روزرسانی جزئی گزینه"),
    destroy=extend_schema(tags=["Admin Surveys"], summary="حذف گزینه"),
)
class AdminOptionViewSet(viewsets.ModelViewSet):
    queryset = Option.objects.all().order_by("order")
    serializer_class = AdminOptionSerializer
    permission_classes = [permissions.IsAdminUser]


@extend_schema_view(
    list=extend_schema(tags=["Admin Surveys"], summary="لیست سابمیشن‌ها"),
    retrieve=extend_schema(tags=["Admin Surveys"], summary="جزئیات سابمیشن"),
    create=extend_schema(tags=["Admin Surveys"], summary="ایجاد سابمیشن"),
    update=extend_schema(tags=["Admin Surveys"], summary="به‌روزرسانی کامل سابمیشن"),
    partial_update=extend_schema(tags=["Admin Surveys"], summary="به‌روزرسانی جزئی سابمیشن"),
    destroy=extend_schema(tags=["Admin Surveys"], summary="حذف سابمیشن"),
)
class AdminSubmissionViewSet(viewsets.ModelViewSet):
    queryset = Submission.objects.select_related("survey", "user").all().order_by("-id")
    serializer_class = AdminSubmissionSerializer
    permission_classes = [permissions.IsAdminUser]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["survey", "user"]


@extend_schema_view(
    list=extend_schema(tags=["Admin Surveys"], summary="لیست پاسخ‌ها"),
    retrieve=extend_schema(tags=["Admin Surveys"], summary="جزئیات پاسخ"),
    create=extend_schema(tags=["Admin Surveys"], summary="ایجاد پاسخ"),
    update=extend_schema(tags=["Admin Surveys"], summary="به‌روزرسانی کامل پاسخ"),
    partial_update=extend_schema(tags=["Admin Surveys"], summary="به‌روزرسانی جزئی پاسخ"),
    destroy=extend_schema(tags=["Admin Surveys"], summary="حذف پاسخ"),
)
class AdminAnswerViewSet(viewsets.ModelViewSet):
    queryset = Answer.objects.select_related("submission", "question").prefetch_related("selected_options").all()
    serializer_class = AdminAnswerSerializer
    permission_classes = [permissions.IsAdminUser]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["submission"]
    
    
@extend_schema_view(
    list=extend_schema(tags=["Admin Tickets"], summary="لیست تیکت‌ها"),
    retrieve=extend_schema(tags=["Admin Tickets"], summary="جزئیات تیکت"),
    create=extend_schema(tags=["Admin Tickets"], summary="ایجاد تیکت"),
    update=extend_schema(tags=["Admin Tickets"], summary="پاسخ/به‌روزرسانی کامل تیکت"),
    partial_update=extend_schema(tags=["Admin Tickets"], summary="ثبت پاسخ تیکت"),
    destroy=extend_schema(tags=["Admin Tickets"], summary="حذف تیکت"),
)
class AdminTicketViewSet(viewsets.ModelViewSet):

    queryset = Ticket.objects.all().order_by("-created_at")
    serializer_class = AdminTicketSerializer
    permission_classes = [permissions.IsAdminUser]

    def perform_update(self, serializer):

        answer = serializer.validated_data.get(
            "answer",
            serializer.instance.answer
        )

        serializer.save(
            is_answered=bool(
                answer and answer.strip()
            )
        )